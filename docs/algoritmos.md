## Algoritmos

Com o objetivo principal de minimizar os tempos médios de espera globais, foi projetada uma arquitetura modular que permite a avaliação comparativa de diferentes abordagens algorítmicas. Abaixo detalham-se os algoritmos a serem estudados, as métricas de avaliação extraídas via SNMP e os cenários de teste aplicados.

- **Algoritmos**: 
  - *Ciclo Fixo (Round-Robin)*: Abordagem de baseline estática. Atribui tempos específicos de abertura do semáforo definidos nas configurações, ignorando o tráfego real.
    - *Objetivo/Análise*: Validar a integração inicial e a mudança de estados na MIB. Fortemente ineficiente em condições reais, pois vias vazias recebem o mesmo tempo que vias congestionadas.

  - *Heuristica de Ocupação*: Abordagem reativa que lê a variável `roadVehicleCount` de cada via de origem. O tempo de verde é distribuído de forma diretamente proporcional à carga atual de trânsito em cada via.
    - *Objetivo/Análise*: Apresenta uma melhoria substancial face ao ciclo fixo, escoando rapidamente vias com elevado fluxo. Contudo, tem o risco de causar starvation (vias secundárias esperam indefinidamente) e ignora a capacidade das vias de destino

  - *Controlo por Backpressure*: O algoritmo calcula a diferença entre o volume de tráfego na via de origem e o espaço livre na via de destino. Apenas atribui "verde" se a via de destino tiver capacidade para receber os veículos.
    - *Objetivo/Análise*: Evita o efeito dominó no trânsito, se a rua da frente ficar completamente cheia (`roadMaxCap`), o sistema corta o verde aos carros que vêm da rua de trás.

  - *Aprendizagem por Reforço*: Solução onde um agente aprende a política ótima de computação de semáforos por tentativa e erro, recebendo uma recompensa sempre que o tempo de espera global da rede diminui.
    - *Objetivo/Análise*: Altamente adaptável a padrões complexos de tráfego a longo prazo, embora exija uma fase inicial de treino prolongada e maior complexidade de implementação.


- **Métricas**: 
  - *Tempo médio de espera global*: Mede o tempo médio que os veículos passam retidos em semáforos vermelhos em toda a rede.

  - *Throughput Global (Capacidade de escoar o trânsito da rede)*: Capacidade da rede de processar veículos, medida pelo número de carros que atingem os sumidouros por minuto.

  - *Nº de Lotação Máxima*: Regista o número de vezes que qualquer via interna da rede atinge 100% da sua capacidade (`roadVehicleCount` = `roadMaxCap`), obrigando à paragem forçada dos cruzamentos anteriores.

  - *Resiliência a Picos*: Mede o número de ciclos de simulação necessários para a rede normalizar e escoar uma via após uma injeção drástica e repentina de tráfego. 

- **Cenários**: 
  - *Tráfego Simétrico*: Injeção do mesmo valor de RGT em todas as vias de entrada em simultâneo (set 1 30, set 2 30, set 3 30)

  - *Pico Localizado*: Aplicação de um RGT extremo numa única via de origem, mantendo as restantes com valores residuais (ex: set 1 100, set 2 10).

  - *Bottleneck*: Injeção de RGT elevado em duas vias de origem distintas que desaguam obrigatoriamente no mesmo cruzamento ou via de destino.