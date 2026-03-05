# Descrição: Bateria de Testes Unificada (Básicos + Complexos) para SD e SSFR.

import sistema_decisao
import ssfr
import math

# --- FUNÇÃO AUXILIAR UNIFICADA ---
def criar_via(v_id, cruzamento=None, eixo=None, rgt=0, veiculos=0, cor=1, tempo_falta=0, destinos=None, capacidade=100):
    if destinos is None:
        destinos = []
    
    via = {
        'id': v_id, 
        'rgt': rgt,
        'veiculos_atuais': veiculos,
        'capacidade': capacidade,
        'total_passados': 0
    }
    
    # Se pertencer a um cruzamento (não for um sumidouro passivo), adiciona as propriedades
    if cruzamento is not None:
        via['cruzamento'] = cruzamento
        via['eixo'] = eixo
        via['semaforo'] = {'cor': cor, 'tempo_falta': tempo_falta, 'destinos': destinos}
        
    return via

def get_via_mock(vias_lista):
    return lambda vid: next((v for v in vias_lista if v['id'] == vid), None)

# ==========================================
# BLOCO 1: TESTES BÁSICOS (1 CRUZAMENTO)
# ==========================================

def test_heuristica_exclusao_mutua():
    print("[Teste 1] SD: Heurística da Maior Fila e Exclusão Mútua")
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=50, cor=1, destinos=[{'via_id': 5, 'ritmo_saida': 20}]),
        criar_via(3, cruzamento=1, eixo='EO', veiculos=10, cor=1, destinos=[{'via_id': 5, 'ritmo_saida': 20}]),
        criar_via(5) # Destino livre
    ]
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    assert vias[0]['semaforo']['cor'] == 2, "FALHA: A via Norte (com mais carros) devia ter ficado Verde!"
    assert vias[1]['semaforo']['cor'] == 1, "FALHA: A via Este devia ter ficado Vermelha (Exclusão Mútua)!"
    print("  -> OK: O Norte abriu e o Este ficou trancado.")

def test_prevencao_deadlock():
    print("[Teste 2] SD: Prevenção de Deadlock (Destino Lotado)")
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=50, cor=1, destinos=[{'via_id': 5, 'ritmo_saida': 20}]),
        criar_via(5, veiculos=95, capacidade=100) # Destino quase lotado (> 90%)
    ]
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    assert vias[0]['semaforo']['cor'] == 1, "FALHA: O sinal abriu mesmo com o destino lotado!"
    print("  -> OK: O sinal recusou-se a abrir porque o destino não tem espaço.")

def test_transicao_amarelo():
    print("[Teste 3] SD: Transição segura para Amarelo")
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=10, cor=2, tempo_falta=0, destinos=[{'via_id': 5, 'ritmo_saida': 20}]),
        criar_via(3, cruzamento=1, eixo='EO', veiculos=10, cor=1),
        criar_via(5)
    ]
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    assert vias[0]['semaforo']['cor'] == 3, "FALHA: O sinal devia ter passado a Amarelo!"
    assert vias[0]['semaforo']['tempo_falta'] == 3, "FALHA: O tempo de Amarelo não foi aplicado!"
    print("  -> OK: O sinal Verde passou corretamente a Amarelo.")

def test_ssfr_entrada_rgt():
    print("[Teste 4] SSFR: Entrada de Veículos via RGT")
    vias = [criar_via(1, rgt=60, veiculos=0)]
    ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    assert vias[0]['veiculos_atuais'] == 5, f"FALHA: Entraram {vias[0]['veiculos_atuais']} carros em vez de 5!"
    print("  -> OK: A matemática do RGT injetou os veículos corretamente.")

def test_ssfr_atravessamento_e_contadores():
    print("[Teste 5] SSFR: Atravessamento e Incremento de Estatísticas")
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=10, cor=2, destinos=[{'via_id': 5, 'ritmo_saida': 60}]),
        criar_via(5)
    ]
    ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    assert vias[0]['veiculos_atuais'] == 5, "FALHA: Os carros não saíram da origem!"
    assert vias[1]['veiculos_atuais'] == 5, "FALHA: Os carros não chegaram ao destino!"
    assert vias[0]['total_passados'] == 5, "FALHA: O OID de total_passados não foi incrementado!"
    print("  -> OK: Os veículos atravessaram e o Throughput foi contabilizado.")


# ==========================================
# BLOCO 2: TESTES COMPLEXOS (MÚLTIPLOS CRUZAMENTOS)
# ==========================================

def test_onda_verde_antecipacao():
    print("\n[Teste 6] SD Complexo: Ativação da Onda Verde (Antecipação)")
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=20, cor=2, destinos=[{'via_id': 2}]),
        criar_via(3, cruzamento=1, eixo='EO', veiculos=0, cor=1),
        criar_via(2, cruzamento=2, eixo='NS', veiculos=0, cor=1, destinos=[{'via_id': 99}]),
        criar_via(4, cruzamento=2, eixo='EO', veiculos=5, cor=1, destinos=[{'via_id': 98}]),
        criar_via(99), criar_via(98)
    ]
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    assert vias[2]['semaforo']['cor'] == 2, "FALHA ONDA VERDE: A Via 2 devia ter ficado Verde!"
    assert vias[3]['semaforo']['cor'] == 1, "FALHA SEGURANÇA: A Via 4 devia ter ficado Vermelha!"
    print("  -> OK: O Cruzamento 2 antecipou o pelotão e ativou a Onda Verde.")

def test_onda_verde_com_deadlock():
    print("\n[Teste 7] SD Complexo: Colisão de Onda Verde com Deadlock (Fallback)")
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=20, cor=2, destinos=[{'via_id': 2}]),
        criar_via(3, cruzamento=1, eixo='EO', veiculos=0, cor=1),
        criar_via(2, cruzamento=2, eixo='NS', veiculos=0, cor=1, destinos=[{'via_id': 99}]),
        criar_via(4, cruzamento=2, eixo='EO', veiculos=5, cor=1, destinos=[{'via_id': 98}]),
        criar_via(99, veiculos=100, capacidade=100), # LOTADO!
        criar_via(98, capacidade=100)
    ]
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    assert vias[2]['semaforo']['cor'] == 1, "FALHA DEADLOCK: A Via 2 abriu para um destino lotado!"
    assert vias[3]['semaforo']['cor'] == 2, "FALHA OTIMIZAÇÃO: A Via 4 devia ter aberto!"
    print("  -> OK: O sistema rejeitou a Onda Verde para evitar Deadlock e abriu a transversal.")

def test_isolamento_cruzamentos():
    print("\n[Teste 8] SD Complexo: Isolamento Matemático de Cruzamentos")
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=10, cor=1, destinos=[{'via_id': 99}]),
        criar_via(3, cruzamento=1, eixo='EO', veiculos=2, cor=1, destinos=[{'via_id': 98}]),
        criar_via(2, cruzamento=2, eixo='NS', veiculos=0, cor=1, destinos=[{'via_id': 97}]),
        criar_via(4, cruzamento=2, eixo='EO', veiculos=80, cor=1, destinos=[{'via_id': 96}]), # Engarrafamento!
        criar_via(99), criar_via(98), criar_via(97), criar_via(96)
    ]
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    assert vias[0]['semaforo']['cor'] == 2, "FALHA ISOLAMENTO: A Via 1 do Cruzamento 1 devia abrir!"
    assert vias[1]['semaforo']['cor'] == 1, "FALHA ISOLAMENTO: A Via 3 do Cruzamento 1 devia fechar!"
    assert vias[2]['semaforo']['cor'] == 1, "FALHA ISOLAMENTO: A Via 2 do Cruzamento 2 devia fechar!"
    assert vias[3]['semaforo']['cor'] == 2, "FALHA ISOLAMENTO: A Via 4 do Cruzamento 2 devia abrir!"
    print("  -> OK: Cruzamentos reagiram de forma independente às pressões locais.")

# Reutiliza a função criar_via e get_via_mock do teu ficheiro anterior

def test_distribuicao_proporcional_fork():
    print("\n[Teste 9] SSFR Complexo: Distribuição em Bifurcação (Flow Split)")
    # Via 10 tem 60 carros. Ritmo total = 40+20 = 60 carros/min.
    # Num step de 5s, devem sair: (60 * 5) / 60 = 5 carros no total.
    # Proporção: 3.33 para Via 11 e 1.66 para Via 12.
    vias = [
        criar_via(10, cruzamento=3, eixo='NS', veiculos=60, cor=2, 
                  destinos=[{'via_id': 11, 'ritmo_saida': 40}, {'via_id': 12, 'ritmo_saida': 20}]),
        criar_via(11, capacidade=100),
        criar_via(12, capacidade=100)
    ]
    
    ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    
    # Verificação de precisão (usando math.isclose para lidar com floats de RGT/taxa)
    assert math.isclose(vias[1]['veiculos_atuais'], 3.333, rel_tol=0.01), "FALHA: Via 11 não recebeu a quota proporcional!"
    assert math.isclose(vias[2]['veiculos_atuais'], 1.666, rel_tol=0.01), "FALHA: Via 12 não recebeu a quota proporcional!"
    assert math.isclose(vias[0]['veiculos_atuais'], 55.0, rel_tol=0.01), "FALHA: Saída total de veículos incorreta!"
    print("  -> OK: O tráfego foi dividido corretamente entre os destinos (66% / 33%).")

def test_estabilidade_avg_wait_time():
    print("\n[Teste 10] SSFR Complexo: Integridade da Métrica de Tempo de Espera")
    # Se 10 veículos esperam 5 segundos, o tempo parado acumulado deve crescer linearmente.
    via = criar_via(1, cruzamento=1, eixo='NS', veiculos=10, cor=1) # Vermelho
    vias = [via]
    
    # Simular 3 ciclos (15 segundos reais)
    for _ in range(3):
        ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    
    # Total parado acumulado = 10 carros * 5s * 3 ciclos = 150 s*veiculo
    # Como nenhum passou, Avg Wait = 150 / 10 = 15 segundos
    assert via['avg_wait_time'] == 15, f"FALHA: Tempo médio de espera ({via['avg_wait_time']}) incoerente!"
    print("  -> OK: A métrica roadAverageWaitTime reflete a realidade da espera")

def test_pressao_extrema_e_prioridade():
    print("\n[Teste 11] SD Complexo: Saturação de Múltiplos Eixos (Stress Test)")
    # Ambos os eixos estão muito cheios, mas o NS tem uma "Onda Verde" vinda de trás
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=80, cor=1, destinos=[{'via_id': 5}]), # Muito cheio
        criar_via(2, cruzamento=1, eixo='EO', veiculos=85, cor=1, destinos=[{'via_id': 5}]), # Ligeiramente mais cheio
        criar_via(10, cruzamento=0, eixo='NS', veiculos=50, cor=2, destinos=[{'via_id': 1}]), # Vindo a Norte
        criar_via(5, capacidade=200)
    ]
    
    # Sem antecipação, o EO abriria (85 > 80).
    # Com antecipação de Onda Verde, o NS ganha pressão virtual: 80 + (50 * 1.5) = 155.
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    
    assert vias[0]['semaforo']['cor'] == 2, "FALHA: O SD não priorizou a Onda Verde sob pressão!"
    assert vias[1]['semaforo']['cor'] == 1, "FALHA: Segurança violada, ambos abertos?"
    print("  -> OK: A heurística de Onda Verde superou a ocupação estática local")

def test_vias_sem_saida_escoamento():
    print("\n[Teste 12] SSFR Complexo: Escoamento para fora da rede (Sumidouro)")
    # Corrigido: Adicionado 'ritmo_saida' para evitar o KeyError
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=20, cor=2, 
                  destinos=[{'via_id': 999, 'ritmo_saida': 60}]) # 999 representa fora da rede
    ]
    ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    
    assert vias[0]['veiculos_atuais'] < 20, "FALHA: Veículos não escoaram para fora da rede!"
    print(f"  -> OK: {20 - vias[0]['veiculos_atuais']:.1f} veículos saíram do sistema.")


# --- EXECUTOR ---
if __name__ == "__main__":
    print("=== BATERIA DE TESTES UNIFICADA (Fase A) ===")
    try:
        test_heuristica_exclusao_mutua()
        test_prevencao_deadlock()
        test_transicao_amarelo()
        test_ssfr_entrada_rgt()
        test_ssfr_atravessamento_e_contadores()
        test_onda_verde_antecipacao()
        test_onda_verde_com_deadlock()
        test_isolamento_cruzamentos()
        test_distribuicao_proporcional_fork()
        test_estabilidade_avg_wait_time()
        test_pressao_extrema_e_prioridade()
        test_vias_sem_saida_escoamento()
        print("\n✅ EXCELENTE! TODOS OS 12 TESTES PASSARAM COM SUCESSO.")
        print("A tua lógica de simulação e decisão está completamente validada.")
    except AssertionError as e:
        print(f"\n❌ ERRO DETETADO NO CÓDIGO: {e}")