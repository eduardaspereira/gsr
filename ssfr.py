# ======================================================================================================
# Autores:
# Unidade Curricular: Gestão e Segurança de Redes (2025/2026)
# Ficheiro: ssfr.py
# Descrição: Componente de Simulação do Fluxo Rodoviário que corre localmente no SC. 
#           Simula o comportamento físico da rede num passo virtual de 5 segundos, injetando veículos através 
#           dos RGT e processando o atravessamento de semáforos entre vias de origem e destino. 
#           Calcula estatísticas de performance, como o tempo médio de espera e o número total de veículos escoados.
#           Retorna estatísticas acumulativas por passo (veículos entrados/saídos) para os escalares globais.
# ======================================================================================================

def simulate_step(vias, get_via_func, step):
    """
    Executa um passo de simulação e retorna estatísticas do passo.
    Retorna: dict com 'entered' (veículos injetados via RGT) e 'exited' (veículos escoados para fora da rede).
    """
    step_entered = 0.0
    step_exited = 0.0

    # 1. Entrada contínua de veículos (RGT) nas vias
    for via in vias:
        rgt = via.get('rgt', 0)
        if rgt > 0:
            novos = (rgt * step) / 60.0
            antes = via.get('veiculos_atuais', 0)
            via['veiculos_atuais'] = min(via.get('capacidade', 100), antes + novos)
            injectados = via['veiculos_atuais'] - antes
            step_entered += injectados

    # 2. Atravessamento dos semáforos (Verde = 2, Amarelo = 3 na MIB)
    for via in vias:
        semaforo = via.get('semaforo')
        if not semaforo or semaforo.get('cor') not in [2, 3]:
            # Veículos parados a vermelho acumulam tempo de espera
            if semaforo and semaforo.get('cor') == 1 and via.get('veiculos_atuais', 0) > 0:
                via['wait_accumulator'] = via.get('wait_accumulator', 0) + via['veiculos_atuais'] * step
                via['wait_samples'] = via.get('wait_samples', 0) + via['veiculos_atuais']
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
                # Estatísticas por via e por link
                via['total_cars_passed'] = via.get('total_cars_passed', 0) + quantidade_a_passar
                destino['cars_passed'] = destino.get('cars_passed', 0) + quantidade_a_passar
            elif not via_dest:
                # Escoamento para fora da rede simulada
                via['veiculos_atuais'] -= quantidade_a_passar
                via['total_cars_passed'] = via.get('total_cars_passed', 0) + quantidade_a_passar
                destino['cars_passed'] = destino.get('cars_passed', 0) + quantidade_a_passar
                step_exited += quantidade_a_passar

    # 3. Escoamento automático de vias sink (sem semáforo, drenam ao drain_rate)
    for via in vias:
        if via.get('tipo') == 'sink' and 'semaforo' not in via:
            drain = via.get('drain_rate', 0)
            if drain > 0 and via.get('veiculos_atuais', 0) > 0:
                drenados = min(via['veiculos_atuais'], (drain * step) / 60.0)
                via['veiculos_atuais'] -= drenados
                step_exited += drenados

    # 4. Cálculo do tempo médio de espera por via
    for via in vias:
        if 'semaforo' in via:
            samples = via.get('wait_samples', 0)
            if samples > 0:
                via['avg_wait_time'] = via.get('wait_accumulator', 0) / samples
            else:
                via['avg_wait_time'] = 0

    return {'entered': step_entered, 'exited': step_exited}