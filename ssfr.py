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
    # 1. Entrada contínua de veículos (RGT) nas vias de origem e métricas de tempo
    for via in vias:
        novos = (via.get('rgt', 0) * step) / 60.0
        via['veiculos_atuais'] = min(via.get('capacidade', 100), via.get('veiculos_atuais', 0) + novos)
        
        # Inicialização segura de contadores de estatísticas (Independente)
        if 'total_passados' not in via:
            via['total_passados'] = 0
        if 'tempo_parado_acumulado' not in via:
            via['tempo_parado_acumulado'] = 0
            
        # Adiciona tempo de espera aos veículos que estão parados no vermelho ou amarelo
        if 'semaforo' in via and via['semaforo']['cor'] in [1, 3]:
            via['tempo_parado_acumulado'] += via['veiculos_atuais'] * step
            
        # Calcula o tempo médio de espera (segundos por veículo)
        total_veiculos = via['veiculos_atuais'] + via['total_passados']
        if total_veiculos > 0:
            via['avg_wait_time'] = int(via['tempo_parado_acumulado'] / total_veiculos)
        else:
            via['avg_wait_time'] = 0
        
    # 2. Atravessamento dos semáforos (Verde = 2, Amarelo = 3 na MIB)
    for via in vias:
        semaforo = via.get('semaforo')
        if not semaforo or semaforo.get('cor') not in [2, 3]: 
            continue
            
        for destino in semaforo.get('destinos', []):
            # Usa 0 como porto de abrigo se o ritmo não estiver definido
            ritmo = destino.get('ritmo_saida', 0) 
            taxa_passagem = (ritmo * step) / 60.0
            quantidade_a_passar = min(via['veiculos_atuais'], taxa_passagem)
            
            via_dest = get_via_func(destino['via_id'])
            
            # Verifica se há espaço no destino
            if via_dest and (via_dest['veiculos_atuais'] + quantidade_a_passar <= via_dest.get('capacidade', 100)):
                via['veiculos_atuais'] -= quantidade_a_passar
                via_dest['veiculos_atuais'] += quantidade_a_passar
                via['total_passados'] += quantidade_a_passar
            elif not via_dest: 
                # Sem destino definido = Escoamento para fora da rede
                via['veiculos_atuais'] -= quantidade_a_passar
                via['total_passados'] += quantidade_a_passar