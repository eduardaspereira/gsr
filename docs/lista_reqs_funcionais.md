# Sistema Central (SC)
- **[Essencial]** O SC deve atuar como um agente SNMPv2c, respondendo a pedidos GET, GETNEXT e SET.

- **[Essencial]** O SC deve instanciar e manter em memória uma MIB baseada em SMIv2 com os dados da topologia rodoviária.

- **[Básico]** O arranque do SC deve ser alimentado por um ficheiro de configuração único (em formato JSON) que define a rede, os tempos e as capacidades.

# Sistema de Simulação do Fluxo Rodoviário (SSFR)
- **[Essencial]** O SSFR deve atualizar o estado da rede a cada ciclo de simulação (ex: 5 segundos).

- **[Essencial]** O SSFR deve injetar veículos nas vias de entrada de acordo com o Ritmo Gerador de Tráfego (RGT) definido.

- **[Essencial]** O escoamento de veículos entre vias (ou para fora da rede) só deve ocorrer se o semáforo da via origem estiver Verde ou Amarelo e se houver capacidade na via de destino.

# Sistema de Decisão (SD)
- **[Essencial]** O SD deve calcular o tempo de verde/vermelho para cada cruzamento, garantindo que o tempo de amarelo é um valor fixo não sujeito a cálculo.

- **[Básico]** O SD deve atualizar a cor e o tempo restante do semáforo diretamente nos objetos correspondentes na MIB do SC.

- **[Opcional]** O SD deve usar uma heurística baseada na "pressão" (número de veículos) para dar prioridade ao eixo com mais trânsito, prevenindo bloqueios.

# Consola de Monitorização e Controlo (CMC)
- **[Essencial]** A CMC deve atuar como um gestor SNMPv2c, não necessitando de interface gráfica complexa.

- **[Essencial]** A consola deve permitir monitorizar os dados da MIB (como número de veículos e cor do semáforo) numa tabela com atualização periódica.

- **[Essencial]** Deve existir um prompt que permita ao administrador alterar o RGT das vias externamente, gerando pedidos SNMP SET dirigidos ao SC.

- **[Opcional]** A CMC deve realizar uma descoberta dinâmica das vias ativas utilizando a primitiva GETNEXT (SNMP Walk). 