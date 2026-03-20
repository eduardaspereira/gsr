# Sistema Central (SC)
- **[Básico]** O arranque do SC deve ser alimentado por um ficheiro de configuração único (em formato JSON) que define a rede, os tempos e as capacidades.

- **[Básico]** O ficheiro de configuração inicial deve permitir que o sistema arranque com vias já contendo veículos.

- **[Essencial]** O SC deve atuar como um agente SNMPv2c, respondendo a pedidos GET, GETNEXT e SET.

- **[Essencial]** O SC deve instanciar e manter em memória uma MIB baseada em SMIv2 com os dados da topologia rodoviária.

- **[Essencial]** O agente SNMPv2c do SC não deve implementar nesta fase quaisquer mecanismos de segurança (autenticação complexa, confidencialidade ou verificação de integridade).

# Sistema de Simulação do Fluxo Rodoviário (SSFR)
- **[Essencial]** O SSFR deve atualizar o estado da rede a cada ciclo de simulação (ex: 5 segundos).

- **[Essencial]** O SSFR deve injetar veículos nas vias de entrada de acordo com o Ritmo Gerador de Tráfego (RGT) definido.

- **[Essencial]** O escoamento de veículos entre vias (ou para fora da rede) só deve ocorrer se o semáforo da via origem estiver Verde ou Amarelo e se houver capacidade na via de destino.

- **[Essencial]** O SSFR deve ser implementado como um componente interno do próprio SC, permitindo a manipulação direta dos objetos da MIB sem recorrer a comunicações externas (SNMP).

- **[Essencial]** Nas situações em que um semáforo liga a múltiplas vias de destino (bifurcações), o SSFR deve distribuir a passagem dos veículos respeitando o ritmo/percentagem configurado para cada via destino.

- **[Essencial]** O SSFR deve suportar um tipo especial de via de escoamento que não tem vias de destino, limitando-se a retirar veículos da rede simulada a um ritmo fixo.

# Sistema de Decisão (SD)
- **[Básico]** O SD deve atualizar a cor e o tempo restante do semáforo diretamente nos objetos correspondentes na MIB do SC.

- **[Essencial]** O SD deve calcular o tempo de verde/vermelho para cada cruzamento, garantindo que o tempo de amarelo é um valor fixo não sujeito a cálculo.

- **[Essencial]** O SD só deve calcular os novos valores para os tempos de cada cor em intervalos temporais que sejam múltiplos do valor do passo da simulação do SSFR.

- **[Essencial]** O algoritmo do SD deve ter como objetivo minimizar os tempos médios de espera globais de todos os veículos, não sendo relevante minimizar o tempo de espera de um veículo em particular.

- **[Essencial]** O SD também deve ser implementado como um componente interno do SC, acedendo diretamente à MIB.

- **[Opcional]** O SD deve adotar uma abordagem algorítmica evolutiva, permitindo a transição de algoritmos de baseline para heurísticas baseadas na lotação e capacidade de destino, podendo explorar opcionalmente técnicas de Inteligência Artificial para minimização dos tempos de espera.

# Consola de Monitorização e Controlo (CMC)
- **[Essencial]** A CMC deve atuar como um gestor SNMPv2c, não necessitando de interface gráfica complexa.

- **[Essencial]** A consola deve permitir monitorizar os dados da MIB (como número de veículos e cor do semáforo) numa tabela com atualização periódica.

- **[Essencial]** Deve existir um prompt que permita ao administrador alterar o RGT das vias externamente, gerando pedidos SNMP SET dirigidos ao SC.

- **[Opcional]** A CMC deve realizar uma descoberta dinâmica das vias ativas utilizando a primitiva GETNEXT (SNMP Walk). 

- **[Opcional]** A CMC pode permitir ao administrador alterar, em tempo de simulação, não apenas os valores dos RGT, mas também os ritmos de escoamento para fora da rede.

- **[Opcional]** A CMC pode incluir uma interface visual intuitiva que ilustre a topologia da rede, a cor dos semáforos e o volume de tráfego em tempo real.