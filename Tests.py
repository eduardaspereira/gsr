# Autores: [Os teus números/nomes]
# Descrição: Testes unitários para validar a máquina de estados (SD) e a física (SSFR).

import sistema_decisao
import ssfr

# --- FUNÇÕES AUXILIARES ---
def criar_via(v_id, rgt=0, veiculos=0, cor=1, tempo_falta=0, destinos=None, capacidade=80):
    if destinos is None:
        destinos = []
    semaforo = {'cor': cor, 'tempo_falta': tempo_falta, 'destinos': destinos}
    return {
        'id': v_id, 'rgt': rgt, 'veiculos_atuais': veiculos,
        'capacidade': capacidade, 'semaforo': semaforo, 'total_passados': 0
    }

def get_via_mock(vias_lista):
    return lambda vid: next((v for v in vias_lista if v['id'] == vid), None)

# --- TESTES DO SISTEMA DE DECISÃO (SD) ---

def test_heuristica_exclusao_mutua():
    print("[Teste 1] SD: Heurística da Maior Fila e Exclusão Mútua")
    # Cenário: Cruzamento todo a vermelho. Norte tem 50 carros, Este tem 10.
    vias = [
        criar_via(1, veiculos=50, cor=1, destinos=[{'via_id': 5, 'ritmo_saida': 20}]), # Norte
        criar_via(3, veiculos=10, cor=1, destinos=[{'via_id': 5, 'ritmo_saida': 20}]), # Este
        criar_via(5, veiculos=0, capacidade=100) # Destino livre
    ]
    
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    
    assert vias[0]['semaforo']['cor'] == 2, "FALHA: A via Norte (com mais carros) devia ter ficado Verde!"
    assert vias[1]['semaforo']['cor'] == 1, "FALHA: A via Este devia ter ficado Vermelha (Exclusão Mútua)!"
    print("  -> OK: O Norte abriu e o Este ficou trancado.")

def test_prevencao_deadlock():
    print("[Teste 2] SD: Prevenção de Deadlock (Destino Lotado)")
    # Cenário: Norte tem carros e está vermelho. O destino está a 95% da capacidade.
    vias = [
        criar_via(1, veiculos=50, cor=1, destinos=[{'via_id': 5, 'ritmo_saida': 20}]), # Norte
        criar_via(5, veiculos=95, capacidade=100) # Destino quase lotado (> 90%)
    ]
    
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    
    assert vias[0]['semaforo']['cor'] == 1, "FALHA: O sinal abriu mesmo com o destino lotado (Risco de Deadlock)!"
    print("  -> OK: O sinal recusou-se a abrir porque o destino não tem espaço.")

def test_transicao_amarelo():
    print("[Teste 3] SD: Transição segura para Amarelo")
    # Cenário: Norte está verde mas o tempo acabou (0s).
    vias = [
        criar_via(1, veiculos=10, cor=2, tempo_falta=0, destinos=[{'via_id': 5, 'ritmo_saida': 20}]),
        criar_via(3, veiculos=10, cor=1), # Este tem trânsito à espera, logo o Norte tem de fechar
        criar_via(5, veiculos=0)
    ]
    
    sistema_decisao.calcular_decisao(vias, tempo_amarelo_fixo=3, step=5)
    
    assert vias[0]['semaforo']['cor'] == 3, "FALHA: O sinal devia ter passado a Amarelo!"
    assert vias[0]['semaforo']['tempo_falta'] == 3, "FALHA: O tempo de Amarelo não foi aplicado corretamente!"
    print("  -> OK: O sinal Verde passou corretamente a Amarelo com o tempo fixo.")

# --- TESTES DO SISTEMA DE SIMULAÇÃO (SSFR) ---

def test_ssfr_entrada_rgt():
    print("[Teste 4] SSFR: Entrada de Veículos via RGT")
    # Cenário: Via com RGT de 60 carros/min (1 por segundo). Num step de 5s, devem entrar 5 carros.
    vias = [criar_via(1, rgt=60, veiculos=0)]
    
    ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    
    assert vias[0]['veiculos_atuais'] == 5, f"FALHA: Entraram {vias[0]['veiculos_atuais']} carros em vez de 5!"
    print("  -> OK: A matemática do RGT injetou os veículos corretamente.")

def test_ssfr_atravessamento_e_contadores():
    print("[Teste 5] SSFR: Atravessamento e Incremento de Estatísticas")
    # Cenário: Norte a Verde, 10 carros na via. Ritmo de saída é 60 carros/min (5 em 5s).
    vias = [
        criar_via(1, veiculos=10, cor=2, destinos=[{'via_id': 5, 'ritmo_saida': 60}]),
        criar_via(5, veiculos=0)
    ]
    
    ssfr.simulate_step(vias, get_via_mock(vias), step=5)
    
    assert vias[0]['veiculos_atuais'] == 5, "FALHA: Os carros não saíram da origem!"
    assert vias[1]['veiculos_atuais'] == 5, "FALHA: Os carros não chegaram ao destino!"
    assert vias[0]['total_passados'] == 5, "FALHA: O OID de total_passados não foi incrementado!"
    print("  -> OK: Os veículos atravessaram e o Throughput foi contabilizado.")

# --- EXECUTOR ---
if __name__ == "__main__":
    print("=== A INICIAR BATERIA DE TESTES GERAIS ===")
    try:
        test_heuristica_exclusao_mutua()
        test_prevencao_deadlock()
        test_transicao_amarelo()
        test_ssfr_entrada_rgt()
        test_ssfr_atravessamento_e_contadores()
        print("\n✅ TODOS OS TESTES PASSARAM COM SUCESSO! A TUA LÓGICA ESTÁ IMPECÁVEL.")
    except AssertionError as e:
        print(f"\n❌ ERRO DETETADO: {e}")