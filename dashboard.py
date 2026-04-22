import streamlit as st
import pandas as pd
import glob
import os
import time

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(page_title="Dashboard GSR", page_icon="🚦", layout="wide")

st.title("🚦 Dashboard Analítica de Tráfego")
st.markdown("Visualização e Análise de Desempenho dos Algoritmos de Decisão.")

# ==========================================
# 2. MOTOR INTELIGENTE DE LEITURA DE DADOS
# ==========================================
@st.cache_data(ttl=2) 
def carregar_dados():
    ficheiros = glob.glob("historico_simulacao_*.csv")
    
    if not ficheiros:
        return pd.DataFrame(), None

    lista_dfs = []
    # Deteta o ficheiro mais recente para saber qual está a correr agora
    ficheiro_mais_recente = max(ficheiros, key=os.path.getmtime)
    modelo_recente = None

    for f in ficheiros:
        try:
            df = pd.read_csv(f, sep=';')
            df.columns = df.columns.str.strip()
            lista_dfs.append(df)
            
            if f == ficheiro_mais_recente and not df.empty and 'Algoritmo' in df.columns:
                modelo_recente = df['Algoritmo'].iloc[-1]
        except Exception:
            pass
            
    if lista_dfs:
        df_final = pd.concat(lista_dfs, ignore_index=True)
        return df_final, modelo_recente
    return pd.DataFrame(), None

df, modelo_recente = carregar_dados()

# ==========================================
# 3. MENU LATERAL (FILTROS E MODOS)
# ==========================================
st.sidebar.header("⚙️ Painel de Controlo")

if df.empty:
    st.info("A aguardar dados da simulação... Corre o teu algoritmo no `sc.py`!")
else:
    algoritmos_disponiveis = df['Algoritmo'].unique().tolist()
    
    # --- OPÇÃO 1: MODO DE VISUALIZAÇÃO ---
    modo_visualizacao = st.sidebar.radio(
        "Modo de Visualização:",
        ["Comparativo (Todos os Modelos)", "Individual (Modelo Específico)"]
    )
    
    # --- OPÇÃO 2: ALGORITMO A ANALISAR (Só aparece no modo Individual) ---
    modelo_selecionado = None
    if modo_visualizacao == "Individual (Modelo Específico)":
        idx_default = algoritmos_disponiveis.index(modelo_recente) if modelo_recente in algoritmos_disponiveis else 0
        modelo_selecionado = st.sidebar.selectbox(
            "Algoritmo a analisar:", 
            algoritmos_disponiveis, 
            index=idx_default
        )
    
    # --- OPÇÃO 3: MÉTRICA ---
    metrica_escolhida = st.sidebar.selectbox(
        "Métrica a visualizar:",
        ["Fila Maxima", "Ocupacao Media", "Total Escoados"]
    )
    
    st.sidebar.markdown("---")
    
    # O BOTÃO MÁGICO DO REFRESH
    auto_refresh = st.sidebar.toggle("Auto-Atualizar (5s)", value=False)
    st.sidebar.markdown("*Dica: Se o botão estiver desligado, usa o **F5** para atualizar manualmente.*")

    # ----------------------------------------------------
    # ASSINATURA DOS ENGENHEIROS (COM FOTOS)
    # ----------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Dashboard desenvolvida por:**")

    def mostrar_perfil(nome_ficheiro, nome_pessoa):
        col_foto, col_nome = st.sidebar.columns([1, 3])
        with col_foto:
            if os.path.exists(nome_ficheiro):
                st.image(nome_ficheiro, use_container_width=True)
            else:
                st.markdown("<h2 style='text-align: center; margin:0;'>👤</h2>", unsafe_allow_html=True)
        with col_nome:
            st.markdown(f"<p style='margin-top: 10px;'><b>{nome_pessoa}</b></p>", unsafe_allow_html=True)

    mostrar_perfil("eduarda.png", "Eduarda Pereira")
    mostrar_perfil("goncalo_f.png", "Gonçalo Ferreira")
    mostrar_perfil("goncalo_m.png", "Gonçalo Magalhães")


    # ==========================================
    # 4. LÓGICA DE VISUALIZAÇÃO E GRÁFICOS
    # ==========================================
    if modo_visualizacao == "Individual (Modelo Específico)":
        # === ZONA EXCLUSIVA DO MODO INDIVIDUAL ===
        df_filtrado = df[df['Algoritmo'] == modelo_selecionado]
        st.subheader(f"Evolução Temporal: **{modelo_selecionado}**")
        
        if metrica_escolhida in df_filtrado.columns:
            df_grafico = df_filtrado.set_index("Tempo (s)")[metrica_escolhida]
            st.line_chart(df_grafico, height=450)
            
        # A tabela de dados brutos
        st.markdown("---")
        st.subheader("Dados Brutos (Logs da Simulação)")
        st.dataframe(df_filtrado.tail(8), use_container_width=True)
            
    else:
        # === ZONA EXCLUSIVA DO MODO COMPARATIVO ===
        st.subheader("Comparação Global de Algoritmos")
        
        if metrica_escolhida in df.columns:
            # 1. Gráfico Principal (Evolução)
            df_grafico = df.pivot(index="Tempo (s)", columns="Algoritmo", values=metrica_escolhida)
            st.line_chart(df_grafico, height=400)
            
            st.markdown("---")
            st.subheader("Resumo de Desempenho (Último Instante)")
            
            # 2. Cálculos para o Ranking
            ultimos_valores = df.groupby('Algoritmo')[metrica_escolhida].last().reset_index()
            
            if metrica_escolhida == "Total Escoados":
                vencedor = ultimos_valores.loc[ultimos_valores[metrica_escolhida].idxmax()]
                ordem_sort = False 
            else:
                vencedor = ultimos_valores.loc[ultimos_valores[metrica_escolhida].idxmin()]
                ordem_sort = True  
                
            ultimos_valores = ultimos_valores.sort_values(by=metrica_escolhida, ascending=ordem_sort).reset_index(drop=True)
            
            # 3. Desenhar os Cartões (KPIs)
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(label="Líder Atual", value=vencedor['Algoritmo'])
            with col2:
                st.metric(label=f"Melhor {metrica_escolhida}", value=round(vencedor[metrica_escolhida], 2))
            with col3:
                pior_valor = ultimos_valores[metrica_escolhida].iloc[-1]
                st.metric(label=f"Pior {metrica_escolhida}", value=round(pior_valor, 2))

            # 4. Gráfico de Barras do Ranking Final
            st.markdown("<br>", unsafe_allow_html=True) 
            st.write(f"**Ranking Final: {metrica_escolhida}**")
            st.bar_chart(ultimos_valores.set_index('Algoritmo'), height=250)

# ==========================================
# 5. MOTOR DE AUTO-REFRESH
# ==========================================
if 'auto_refresh' in locals() and auto_refresh:
    time.sleep(5)
    st.rerun()