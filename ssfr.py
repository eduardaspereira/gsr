# ======================================================================================================
# Autores:
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: sistema_decisao.py
# Descrição: Componente de Simulação do Fluxo Rodoviário que corre localmente no SC. 
#           Simula o comportamento físico da rede num passo virtual de 5 segundos, injetando veículos através 
#           dos RGT e processando o atravessamento de semáforos entre vias de origem e destino. 
#           Calcula estatísticas de performance, como o tempo médio de espera e o número total de veículos escoados.
# ======================================================================================================

def simulate_step(vias, get_via_func, step):
    # 1. Entrada contínua de veículos (RGT) nas vias
    for via in vias:
        novos = (via.get('rgt', 0) * step) / 60.0
        via['veiculos_atuais'] = min(via.get('capacidade', 100), via.get('veiculos_atuais', 0) + novos)

    # 2. Atravessamento dos semáforos (Verde = 2, Amarelo = 3 na MIB)
    for via in vias:
        semaforo = via.get('semaforo')
        if not semaforo or semaforo.get('cor') not in [2, 3]:
            continue

        for destino in semaforo.get('destinos', []):
            ritmo = destino.get('ritmo_saida', 0)
            taxa_passagem = (ritmo * step) / 60.0
            quantidade_a_passar = min(via.get('veiculos_atuais', 0), taxa_passagem)

            via_dest = get_via_func(destino['via_id'])

            # Verifica se ha espaco no destino; se nao existir destino, escoa para fora da rede
            if via_dest and (via_dest.get('veiculos_atuais', 0) + quantidade_a_passar <= via_dest.get('capacidade', 100)):
                via['veiculos_atuais'] -= quantidade_a_passar
                via_dest['veiculos_atuais'] += quantidade_a_passar
            elif not via_dest:
                via['veiculos_atuais'] -= quantidade_a_passar