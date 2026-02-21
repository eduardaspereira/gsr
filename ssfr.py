def simulate_step(vias, get_via_func, step):
    # 1. Entrada contínua de veículos (RGT) nas vias de origem
    for via in vias:
        novos = (via.get('rgt', 0) * step) / 60.0
        via['veiculos_atuais'] = min(via.get('capacidade', 100), via.get('veiculos_atuais', 0) + novos)
        
    # 2. Atravessamento dos semáforos (Verde = 2, Amarelo = 3 na MIB)
    for via in vias:
        semaforo = via.get('semaforo')
        if not semaforo or semaforo.get('cor') not in [2, 3]: 
            continue
            
        for destino in semaforo.get('destinos', []):
            taxa_passagem = (destino['ritmo_saida'] * step) / 60.0
            quantidade_a_passar = min(via['veiculos_atuais'], taxa_passagem)
            
            via_dest = get_via_func(destino['via_id'])
            
            # Verifica se há espaço no destino
            if via_dest and (via_dest['veiculos_atuais'] + quantidade_a_passar <= via_dest.get('capacidade', 100)):
                via['veiculos_atuais'] -= quantidade_a_passar
                via_dest['veiculos_atuais'] += quantidade_a_passar
            elif not via_dest: 
                # Sem destino definido = Escoamento para fora da rede
                via['veiculos_atuais'] -= quantidade_a_passar