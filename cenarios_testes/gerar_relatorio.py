import pandas as pd
import matplotlib.pyplot as plt
import os

# =================================================================
# 1. CONFIGURAÇÕES DE VISUAL
# =================================================================
cores = {
    "ROUND_ROBIN": "#E63946",   # Vermelho
    "HEURISTICA": "#F4A261",    # Laranja
    "RL": "#2A9D8F",            # Verde/Azul
    "BACKPRESSURE": "#264653"   # Azul Escuro
}

# O que vamos analisar em cada um dos teus ficheiros Excel
cenarios_setup = {
    "Cenario1": {"metrica": "Ocupacao Media", "titulo": "Cenário 1: Tráfego Leve (Ocupação Média da Rede)"},
    "Cenario2": {"metrica": "Fila Maxima", "titulo": "Cenário 2: Desequilíbrio (Crescimento de Fila Máxima)"},
    "Cenario3": {"metrica": "Total Escoados", "titulo": "Cenário 3: Saturação (Veículos Processados)"}
}

# =================================================================
# 2. MOTOR DE GERAÇÃO
# =================================================================
print("A ler os ficheiros Excel e a gerar gráficos...\n")

for cenario, config in cenarios_setup.items():
    ficheiro_excel = f"{cenario}.xlsx"
    metrica = config["metrica"]
    
    if not os.path.exists(ficheiro_excel):
        print(f"Falta o ficheiro: {ficheiro_excel}. Avançando...")
        continue
        
    print(f"A processar {ficheiro_excel}...")
    
    # Lê o Excel mágico que tu criaste!
    df = pd.read_excel(ficheiro_excel)
    
    # Prepara a tela
    plt.figure(figsize=(10, 6), dpi=300)
    plt.title(config["titulo"], fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Tempo de Simulação (Segundos)", fontsize=12)
    plt.ylabel(metrica, fontsize=12)
    
    # Vai à coluna "Algoritmo" e descobre quais lá estão (RR, RL, etc.)
    algoritmos_no_excel = df['Algoritmo'].unique()
    
    for alg in algoritmos_no_excel:
        # Filtra os dados só para este algoritmo
        dados_alg = df[df['Algoritmo'] == alg]
        
        # Desenha a linha
        if alg in cores:
            cor_linha = cores[alg]
        else:
            cor_linha = "black" # Cor de segurança caso haja algum nome diferente
            
        plt.plot(dados_alg['Tempo (s)'], dados_alg[metrica], 
                 label=alg, color=cor_linha, linewidth=2.5, marker='o', markevery=3)
                 
    # Embelezar e Guardar
    plt.legend(title="Sistemas de Decisão", loc="best", framealpha=0.9)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    
    nome_imagem = f"GRAFICO_FINAL_{cenario}.png"
    plt.savefig(nome_imagem)
    print(f" Guardado: {nome_imagem}")
    plt.close()

print("\nDone")