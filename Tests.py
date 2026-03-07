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
        'capacidade': capacidade
    }
    
    # Se pertencer a um cruzamento (não for um sumidouro passivo), adiciona as propriedades
    if cruzamento is not None:
        via['cruzamento'] = cruzamento
        via['eixo'] = eixo
        via['semaforo'] = {'cor': cor, 'tempo_falta': tempo_falta, 'destinos': destinos, 'green_duration': 0, 'red_duration': 0}
        
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

def test_transicao_amarelo():
    print("[Teste 2] SD: Transição segura para Amarelo")
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
    print("[Teste 3] SSFR: Entrada de Veículos via RGT")
    vias = [criar_via(1, rgt=60, veiculos=0)]
    ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    assert vias[0]['veiculos_atuais'] == 5, f"FALHA: Entraram {vias[0]['veiculos_atuais']} carros em vez de 5!"
    print("  -> OK: A matemática do RGT injetou os veículos corretamente.")

def test_ssfr_atravessamento():
    print("[Teste 4] SSFR: Atravessamento de Veiculos")
    vias = [
        criar_via(1, cruzamento=1, eixo='NS', veiculos=10, cor=2, destinos=[{'via_id': 5, 'ritmo_saida': 60}]),
        criar_via(5)
    ]
    ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    assert vias[0]['veiculos_atuais'] == 5, "FALHA: Os carros não saíram da origem!"
    assert vias[1]['veiculos_atuais'] == 5, "FALHA: Os carros não chegaram ao destino!"
    print("  -> OK: Os veículos atravessaram para o destino corretamente.")


def test_distribuicao_proporcional_fork():
    print("\n[Teste 5] SSFR: Distribuição em Bifurcação (Flow Split)")
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
def test_vias_sem_saida_escoamento():
    print("\n[Teste 6] SSFR: Escoamento para fora da rede (Sumidouro)")
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
        test_transicao_amarelo()
        test_ssfr_entrada_rgt()
        test_ssfr_atravessamento()
        test_distribuicao_proporcional_fork()
        test_vias_sem_saida_escoamento()
        print("\n✅ EXCELENTE! TODOS OS 6 TESTES PASSARAM COM SUCESSO.")
        print("A tua lógica de simulação e decisão está completamente validada.")
    except AssertionError as e:
        print(f"\n❌ ERRO DETETADO NO CÓDIGO: {e}")