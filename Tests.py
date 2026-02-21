 
# Descrição: Bateria de Testes Unificada (Básicos + Complexos) para SD e SSFR.

import sistema_decisao
import ssfr

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
        print("\n✅ EXCELENTE! TODOS OS 8 TESTES PASSARAM COM SUCESSO.")
        print("A tua lógica de simulação e decisão está completamente validada.")
    except AssertionError as e:
        print(f"\n❌ ERRO DETETADO NO CÓDIGO: {e}")