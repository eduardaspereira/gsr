# Autores: [Os teus números/nomes]
# Descrição: Módulo de decisão inteligente com exclusão mútua (Fases de Tráfego)
#            e Heurística de Maximização de Escoamento.

def calcular_decisao(vias_data, tempo_amarelo_fixo, step):
    # 1. Definir os grupos de conflito (Fases) com base nos IDs do config.json
    vias_ns = [v for v in vias_data if v['id'] in [1, 2]] # Eixo Norte-Sul
    vias_eo = [v for v in vias_data if v['id'] in [3, 4]] # Eixo Este-Oeste

    # Função auxiliar para saber o estado atual de um eixo
    def obter_estado_fase(grupo):
        cores = [v['semaforo']['cor'] for v in grupo if 'semaforo' in v]
        if 2 in cores: return 2 # Verde
        if 3 in cores: return 3 # Amarelo
        return 1 # Vermelho

    estado_ns = obter_estado_fase(vias_ns)
    estado_eo = obter_estado_fase(vias_eo)

    # 2. Atualizar contadores de tempo
    for via in vias_data:
        if 'semaforo' in via:
            via['semaforo']['tempo_falta'] -= step

    # 3. Lógica de Máquina de Estados e Transições
    
    # REGRA 1: Segurança Máxima (Lidar com o Amarelo)
    # Se uma fase está a passar para vermelho, bloqueia qualquer outra ação.
    if estado_ns == 3:
        for via in vias_ns:
            if via['semaforo']['cor'] == 3 and via['semaforo']['tempo_falta'] <= 0:
                via['semaforo']['cor'] = 1
                print(f"[SD] Eixo Norte-Sul (Via {via['id']}) passou a VERMELHO.")
        return 

    if estado_eo == 3:
        for via in vias_eo:
            if via['semaforo']['cor'] == 3 and via['semaforo']['tempo_falta'] <= 0:
                via['semaforo']['cor'] = 1
                print(f"[SD] Eixo Este-Oeste (Via {via['id']}) passou a VERMELHO.")
        return 

    # REGRA 2: Fim do Tempo de Verde
    # Avalia se deve estender o verde ou fechar a fase atual.
    if estado_ns == 2:
        ocupacao_concorrente = sum(v.get('veiculos_atuais', 0) for v in vias_eo)
        for via in vias_ns:
            if via['semaforo']['cor'] == 2 and via['semaforo']['tempo_falta'] <= 0:
                # Fecha o sinal se houver carros no outro eixo ou se esta via esvaziou
                if ocupacao_concorrente > 0 or via.get('veiculos_atuais', 0) == 0:
                    via['semaforo']['cor'] = 3
                    via['semaforo']['tempo_falta'] = tempo_amarelo_fixo
                    print(f"[SD] Eixo Norte-Sul a fechar (AMARELO).")
                else:
                    via['semaforo']['tempo_falta'] = 10 # Estende o verde (não há concorrência)
        return

    if estado_eo == 2:
        ocupacao_concorrente = sum(v.get('veiculos_atuais', 0) for v in vias_ns)
        for via in vias_eo:
            if via['semaforo']['cor'] == 2 and via['semaforo']['tempo_falta'] <= 0:
                if ocupacao_concorrente > 0 or via.get('veiculos_atuais', 0) == 0:
                    via['semaforo']['cor'] = 3
                    via['semaforo']['tempo_falta'] = tempo_amarelo_fixo
                    print(f"[SD] Eixo Este-Oeste a fechar (AMARELO).")
                else:
                    via['semaforo']['tempo_falta'] = 10
        return

    # REGRA 3: Exclusão Mútua Cumprida (Todos os sinais estão Vermelhos)
    # Heurística: Qual eixo deve abrir agora para minimizar tempos de espera globais?
    if estado_ns == 1 and estado_eo == 1:
        ocupacao_ns = sum(v.get('veiculos_atuais', 0) for v in vias_ns)
        ocupacao_eo = sum(v.get('veiculos_atuais', 0) for v in vias_eo)

        if ocupacao_ns == 0 and ocupacao_eo == 0:
            return # Sem trânsito na rede, mantém tudo vermelho.

        # Decide abrir a fase com maior número total de veículos
        fase_a_abrir = vias_ns if ocupacao_ns >= ocupacao_eo else vias_eo
        nome_fase = "Norte-Sul" if ocupacao_ns >= ocupacao_eo else "Este-Oeste"

        for via in fase_a_abrir:
            # Proteção extra: Evitar Deadlock olhando para as vias de destino
            pode_abrir = True
            for dest in via['semaforo'].get('destinos', []):
                via_dest = next((v for v in vias_data if v['id'] == dest['via_id']), None)
                if via_dest and (via_dest.get('veiculos_atuais', 0) / via_dest.get('capacidade', 1)) > 0.9:
                    pode_abrir = False # Destino bloqueado, não abre
            
            if pode_abrir and via.get('veiculos_atuais', 0) > 0:
                via['semaforo']['cor'] = 2
                via['semaforo']['tempo_falta'] = 20 # Tempo inicial de verde
                print(f"[SD] Eixo {nome_fase} (Via {via['id']}) a VERDE (Heurística).")