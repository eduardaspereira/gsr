# ======================================================================================================
# Autores:
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: sistema_decisao.py
# Descrição:Implementa a lógica inteligente de controlo de semáforos integrada no SC. 
#           Utiliza uma heurística de pressão baseada em filas, priorizando eixos com maior acumulação de veículos. 
#           Implementa a funcionalidade avançada de "Onda Verde", que antecipa a chegada de pelotões de veículos 
#           de cruzamentos adjacentes para minimizar o tempo global de espera. Inclui mecanismos de segurança para prevenir 
#           deadlocks em vias lotadas
# ======================================================================================================

def obter_estado_fase(grupo):
    cores = [v['semaforo']['cor'] for v in grupo if 'semaforo' in v]
    if 2 in cores: return 2 # Verde
    if 3 in cores: return 3 # Amarelo
    return 1 # Vermelho

def calcular_decisao(vias_data, tempo_amarelo_fixo, step, algo_min_green_time=20):
    # 1. Agrupar as vias pelos seus respetivos cruzamentos
    cruzamentos = {}
    for via in vias_data:
        c_id = via.get('cruzamento')
        if c_id:
            if c_id not in cruzamentos:
                cruzamentos[c_id] = []
            cruzamentos[c_id].append(via)

    # 2. Atualizar contadores de tempo globais
    for via in vias_data:
        if 'semaforo' in via:
            via['semaforo']['tempo_falta'] -= step
            # Acumula tempo de vermelho para cálculo de red_duration
            if via['semaforo']['cor'] == 1:
                via['semaforo']['_red_accumulated'] = via['semaforo'].get('_red_accumulated', 0) + step

    # 3. Executar a máquina de estados para cada cruzamento independentemente
    for c_id, vias_int in cruzamentos.items():
        vias_ns = [v for v in vias_int if v.get('eixo') == 'NS']
        vias_eo = [v for v in vias_int if v.get('eixo') == 'EO']

        estado_ns = obter_estado_fase(vias_ns)
        estado_eo = obter_estado_fase(vias_eo)

        # REGRA 1: Segurança Máxima (Lidar com o Amarelo)
        if estado_ns == 3:
            for via in vias_ns:
                if via['semaforo']['cor'] == 3 and via['semaforo']['tempo_falta'] <= 0:
                    via['semaforo']['cor'] = 1
                    print(f"[SD] Cruzamento {c_id}: Eixo NS passou a VERMELHO.")
            continue 

        if estado_eo == 3:
            for via in vias_eo:
                if via['semaforo']['cor'] == 3 and via['semaforo']['tempo_falta'] <= 0:
                    via['semaforo']['cor'] = 1
                    print(f"[SD] Cruzamento {c_id}: Eixo EO passou a VERMELHO.")
            continue 

        # REGRA 2: Fim do Tempo de Verde (Estende ou Fecha)
        if estado_ns == 2:
            ocupacao_concorrente = sum(v.get('veiculos_atuais', 0) for v in vias_eo)
            for via in vias_ns:
                if via['semaforo']['cor'] == 2 and via['semaforo']['tempo_falta'] <= 0:
                    if ocupacao_concorrente > 0 or via.get('veiculos_atuais', 0) == 0:
                        via['semaforo']['cor'] = 3
                        via['semaforo']['tempo_falta'] = tempo_amarelo_fixo
                    else:
                        via['semaforo']['tempo_falta'] = algo_min_green_time # Estende
                        via['semaforo']['green_duration'] = via['semaforo'].get('green_duration', 0) + algo_min_green_time
            continue

        if estado_eo == 2:
            ocupacao_concorrente = sum(v.get('veiculos_atuais', 0) for v in vias_ns)
            for via in vias_eo:
                if via['semaforo']['cor'] == 2 and via['semaforo']['tempo_falta'] <= 0:
                    if ocupacao_concorrente > 0 or via.get('veiculos_atuais', 0) == 0:
                        via['semaforo']['cor'] = 3
                        via['semaforo']['tempo_falta'] = tempo_amarelo_fixo
                    else:
                        via['semaforo']['tempo_falta'] = algo_min_green_time
                        via['semaforo']['green_duration'] = via['semaforo'].get('green_duration', 0) + algo_min_green_time
            continue

        # REGRA 3: Exclusão Mútua Cumprida (Heurística de ONDA VERDE)
        if estado_ns == 1 and estado_eo == 1:
            pressao_ns = sum(v.get('veiculos_atuais', 0) for v in vias_ns)
            pressao_eo = sum(v.get('veiculos_atuais', 0) for v in vias_eo)

            # Onda Verde (Pressão Virtual / Antecipação)
            for via_ns in vias_ns:
                for via_origem in vias_data:
                    if 'semaforo' in via_origem and via_origem['semaforo']['cor'] == 2:
                        for dest in via_origem['semaforo'].get('destinos', []):
                            if dest['via_id'] == via_ns['id']:
                                pressao_ns += via_origem.get('veiculos_atuais', 0) * 1.5
            
            for via_eo in vias_eo:
                for via_origem in vias_data:
                    if 'semaforo' in via_origem and via_origem['semaforo']['cor'] == 2:
                        for dest in via_origem['semaforo'].get('destinos', []):
                            if dest['via_id'] == via_eo['id']:
                                pressao_eo += via_origem.get('veiculos_atuais', 0) * 1.5

            if pressao_ns == 0 and pressao_eo == 0:
                continue # Sem trânsito na rede, mantém vermelho

            # Ordenamos os eixos pela sua prioridade (maior pressão primeiro)
            fases_ordem = [
                (vias_ns, pressao_ns, "NS"), 
                (vias_eo, pressao_eo, "EO")
            ]
            fases_ordem.sort(key=lambda x: x[1], reverse=True)

            # Tenta abrir o eixo prioritário. Se não conseguir (devido a deadlock), tenta o secundário.
            for fase, pressao, nome_fase in fases_ordem:
                if pressao == 0:
                    continue
                
                fase_abriu_com_sucesso = False
                
                for via in fase:
                    pode_abrir = True
                    # Proteção Extra: Prevenção de Deadlock
                    for dest in via['semaforo'].get('destinos', []):
                        via_dest = next((v for v in vias_data if v['id'] == dest['via_id']), None)
                        if via_dest and (via_dest.get('veiculos_atuais', 0) / via_dest.get('capacidade', 1)) > 0.9:
                            pode_abrir = False 
                    
                    tem_pressao_suficiente = via.get('veiculos_atuais', 0) > 0 or (pressao > sum(v.get('veiculos_atuais', 0) for v in fase))
                    
                    if pode_abrir and tem_pressao_suficiente:
                        via['semaforo']['cor'] = 2
                        via['semaforo']['tempo_falta'] = algo_min_green_time
                        via['semaforo']['green_duration'] = algo_min_green_time
                        via['semaforo']['red_duration'] = via['semaforo'].get('_red_accumulated', 0)
                        via['semaforo']['_red_accumulated'] = 0
                        fase_abriu_com_sucesso = True
                        print(f"[SD] Cruzamento {c_id}: Eixo {nome_fase} (Via {via['id']}) a VERDE. Pressão: {pressao:.1f}")
                
                # Exclusão Mútua: Se conseguimos abrir o eixo prioritário, saímos do loop
                # (Não tentamos abrir o eixo secundário em simultâneo)
                if fase_abriu_com_sucesso:
                    break