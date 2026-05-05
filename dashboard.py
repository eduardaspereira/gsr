# ==============================================================================
# Ficheiro: dashboard.py
# Autores: Eduarda Pereira, Gonçalo Ferreira, Gonçalo Magalhães
# Descrição: Dashboard Analítico (Web). Interface interativa desenvolvida em 
#            Streamlit para visualização em tempo real do desempenho dos 
#            diferentes motores de decisão, lendo os logs CSV do Sistema Central.
# ==============================================================================

import streamlit as st
import pandas as pd
import glob
import os
import time

# ==========================================
# 1. MOTOR INTELIGENTE DE LEITURA DE DADOS
# ==========================================
@st.cache_data(ttl=2) 
def carregar_dados_simulacao():
    """
    Lê todos os ficheiros CSV do histórico gerados pelo Sistema Central.
    Usa cache de 2 segundos (ttl=2) para evitar leituras excessivas ao disco rígido.
    Devolve um DataFrame consolidado e o nome do algoritmo mais recente.
    """
    ficheiros_csv = glob.glob("historico_simulacao_*.csv")
    
    if not ficheiros_csv:
        return pd.DataFrame(), None

    lista_dataframes = []
    # Deteta o ficheiro modificado mais recentemente para saber o algoritmo atual
    ficheiro_mais_recente = max(ficheiros_csv, key=os.path.getmtime)
    modelo_atual = None

    for ficheiro in ficheiros_csv:
        try:
            df = pd.read_csv(ficheiro, sep=';')
            df.columns = df.columns.str.strip()
            lista_dataframes.append(df)
            
            # Se for o ficheiro atual, extrai o nome do algoritmo
            if ficheiro == ficheiro_mais_recente and not df.empty and 'Algoritmo' in df.columns:
                modelo_atual = df['Algoritmo'].iloc[-1]
        except Exception:
            pass # Ignora ficheiros corrompidos ou bloqueados momentaneamente
            
    if lista_dataframes:
        df_consolidado = pd.concat(lista_dataframes, ignore_index=True)
        return df_consolidado, modelo_atual
        
    return pd.DataFrame(), None

# ==========================================
# 2. COMPONENTES VISUAIS DA INTERFACE (UI)
# ==========================================
def renderizar_perfil_autor(nome_ficheiro_imagem, nome_autor):
    """Renderiza a fotografia e o nome de um autor na barra lateral."""
    coluna_foto, coluna_nome = st.sidebar.columns([1, 3])
    with coluna_foto:
        if os.path.exists(nome_ficheiro_imagem):
            st.image(nome_ficheiro_imagem, use_container_width=True)
        else:
            st.markdown("<h2 style='text-align: center; margin:0;'>👤</h2>", unsafe_allow_html=True)
    with coluna_nome:
        st.markdown(f"<p style='margin-top: 10px;'><b>{nome_autor}</b></p>", unsafe_allow_html=True)


def renderizar_modo_individual(df_dados, algoritmo_selecionado, metrica):
    """Desenha os gráficos e tabelas para um único algoritmo."""
    df_filtrado = df_dados[df_dados['Algoritmo'] == algoritmo_selecionado]
    st.subheader(f"Evolução Temporal: **{algoritmo_selecionado}**")
    
    if metrica in df_filtrado.columns:
        df_grafico = df_filtrado.set_index("Tempo (s)")[metrica]
        st.line_chart(df_grafico, height=450)
        
    st.markdown("---")
    st.subheader("Dados Brutos (Logs da Simulação)")
    st.dataframe(df_filtrado.tail(8), use_container_width=True)


def renderizar_modo_comparativo(df_dados, metrica):
    """Desenha os gráficos de comparação entre todos os algoritmos e o Ranking Final."""
    st.subheader("Comparação Global de Algoritmos")
    
    if metrica in df_dados.columns:
        # 1. Gráfico Principal (Evolução Temporal Conjunta)
        df_grafico = df_dados.pivot(index="Tempo (s)", columns="Algoritmo", values=metrica)
        st.line_chart(df_grafico, height=400)
        
        st.markdown("---")
        st.subheader("Resumo de Desempenho (Último Instante)")
        
        # 2. Cálculos para o Ranking Final
        ultimos_registos = df_dados.groupby('Algoritmo')[metrica].last().reset_index()
        
        # A lógica de vitória inverte: Escoados quer-se muito, Filas quer-se pouco
        if metrica == "Total Escoados":
            vencedor = ultimos_registos.loc[ultimos_registos[metrica].idxmax()]
            ordem_ascendente = False 
        else:
            vencedor = ultimos_registos.loc[ultimos_registos[metrica].idxmin()]
            ordem_ascendente = True  
            
        ultimos_registos = ultimos_registos.sort_values(by=metrica, ascending=ordem_ascendente).reset_index(drop=True)
        
        # 3. Desenhar os Cartões de KPI (Key Performance Indicators)
        coluna1, coluna2, coluna3 = st.columns(3)
        
        with coluna1:
            st.metric(label="Líder Atual", value=vencedor['Algoritmo'])
        with coluna2:
            st.metric(label=f"Melhor {metrica}", value=round(vencedor[metrica], 2))
        with coluna3:
            pior_valor = ultimos_registos[metrica].iloc[-1]
            st.metric(label=f"Pior {metrica}", value=round(pior_valor, 2))

        # 4. Gráfico de Barras do Ranking Final
        st.markdown("<br>", unsafe_allow_html=True) 
        st.write(f"**Ranking Final: {metrica}**")
        st.bar_chart(ultimos_registos.set_index('Algoritmo'), height=250)


# ==========================================
# 3. ROTINA PRINCIPAL (MAIN LOOP)
# ==========================================
def main():
    st.set_page_config(page_title="Dashboard GSR", page_icon="🚦", layout="wide")
    
    st.title("🚦 Dashboard Analítico de Tráfego")
    st.markdown("Visualização e Análise de Desempenho dos Algoritmos de Decisão.")

    # Obter dados em tempo real
    df_global, modelo_atual = carregar_dados_simulacao()

    # --- MENU LATERAL (Painel de Controlo) ---
    st.sidebar.header("⚙️ Painel de Controlo")

    if df_global.empty:
        st.info("A aguardar dados da simulação... Executa o Sistema Central (`sc.py`)!")
        return

    algoritmos_disponiveis = df_global['Algoritmo'].unique().tolist()
    
    modo_visualizacao = st.sidebar.radio(
        "Modo de Visualização:",
        ["Comparativo (Todos os Modelos)", "Individual (Modelo Específico)"]
    )
    
    algoritmo_alvo = None
    if modo_visualizacao == "Individual (Modelo Específico)":
        indice_predefinido = algoritmos_disponiveis.index(modelo_atual) if modelo_atual in algoritmos_disponiveis else 0
        algoritmo_alvo = st.sidebar.selectbox(
            "Algoritmo a analisar:", 
            algoritmos_disponiveis, 
            index=indice_predefinido
        )
    
    metrica_selecionada = st.sidebar.selectbox(
        "Métrica a visualizar:",
        ["Fila Maxima", "Ocupacao Media", "Total Escoados"]
    )
    
    st.sidebar.markdown("---")
    
    # Controlo de Auto-Refresh
    atualizacao_automatica = st.sidebar.toggle("Atualização Automática (5s)", value=False)
    st.sidebar.markdown("*Dica: Se estiver desligado, prime **F5** para atualizar.*")

    st.sidebar.markdown("---")
    st.sidebar.markdown("**Dashboard desenvolvido por:**")
    renderizar_perfil_autor("eduarda.png", "Eduarda Pereira")
    renderizar_perfil_autor("goncalo_f.png", "Gonçalo Ferreira")
    renderizar_perfil_autor("goncalo_m.png", "Gonçalo Magalhães")

    # --- RENDERIZAÇÃO DO CONTEÚDO PRINCIPAL ---
    if modo_visualizacao == "Individual (Modelo Específico)":
        renderizar_modo_individual(df_global, algoritmo_alvo, metrica_selecionada)
    else:
        renderizar_modo_comparativo(df_global, metrica_selecionada)

    # Lógica de recarregamento
    if atualizacao_automatica:
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()