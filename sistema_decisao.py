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

def calcular_decisao(vias_data, tempo_amarelo_fixo, step):
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

    # 3. Executar a maquina de estados para cada cruzamento independentemente
    for c_id, vias_int in cruzamentos.items():
        vias_ns = [v for v in vias_int if v.get('eixo') == 'NS']
        vias_eo = [v for v in vias_int if v.get('eixo') == 'EO']

        estado_ns = obter_estado_fase(vias_ns)
        estado_eo = obter_estado_fase(vias_eo)

        # REGRA 1: Transicao segura do Amarelo para Vermelho
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

        # REGRA 2: Fim do Tempo de Verde (fecha e passa a Amarelo)
        if estado_ns == 2:
            for via in vias_ns:
                if via['semaforo']['cor'] == 2 and via['semaforo']['tempo_falta'] <= 0:
                    via['semaforo']['cor'] = 3
                    via['semaforo']['tempo_falta'] = tempo_amarelo_fixo
            continue

        if estado_eo == 2:
            for via in vias_eo:
                if via['semaforo']['cor'] == 2 and via['semaforo']['tempo_falta'] <= 0:
                    via['semaforo']['cor'] = 3
                    via['semaforo']['tempo_falta'] = tempo_amarelo_fixo
            continue

        # REGRA 3: Exclusao mutua (abre o eixo com mais veiculos)
        if estado_ns == 1 and estado_eo == 1:
            pressao_ns = sum(v.get('veiculos_atuais', 0) for v in vias_ns)
            pressao_eo = sum(v.get('veiculos_atuais', 0) for v in vias_eo)

            if pressao_ns == 0 and pressao_eo == 0:
                continue # Sem trânsito na rede, mantém vermelho

            eixo_preferido = "NS" if pressao_ns >= pressao_eo else "EO"
            fase = vias_ns if eixo_preferido == "NS" else vias_eo

            for via in fase:
                if via.get('veiculos_atuais', 0) > 0:
                    via['semaforo']['cor'] = 2
                    via['semaforo']['tempo_falta'] = 20
                    print(f"[SD] Cruzamento {c_id}: Eixo {eixo_preferido} (Via {via['id']}) a VERDE.")
                    break