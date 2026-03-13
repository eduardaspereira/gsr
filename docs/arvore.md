# Modelo de Informação

```
iso(1).org(3).dod(6).internet(1).experimental(3)
 |
 +-- trafficMgmtMIB (2026)
      |
      +-- trafficObjects (1)
           |
           +-- trafficGeneral (1)
           |    |
           |    +-- simStatus (1) .............. [RW] SimOperStatus
           |    +-- simStepDuration (2) ........ [RW] Integer32
           |    +-- simElapsedTime (3) ......... [RO] Counter32
           |    +-- globalVehicleCount (4) ..... [RO] Gauge32
           |    +-- globalAvgWaitTime (5) ...... [RO] Gauge32
           |    +-- totalVehiclesEntered (6) ... [RO] Counter32
           |    +-- totalVehiclesExited (7) .... [RO] Counter32
           |    +-- algoMinGreenTime (8) ....... [RW] Integer32
           |    +-- algoMaxGreenTime (9) ....... [RW] Integer32
           |    +-- algoYellowTime (10) ........ [RO] Integer32
           |
           +-- crossroadTable (2)
           |    |
           |    +-- crossroadEntry (1) [INDEX: crossroadIndex]
           |         |
           |         +-- crossroadIndex (1) ...... [NA] Integer32
           |         +-- crossroadMode (2) ....... [RW] CrossroadMode
           |         +-- crossroadRowStatus (3) .. [RC] RowStatus
           |
           +-- roadTable (3)
           |    |
           |    +-- roadEntry (1) [INDEX: roadIndex]
           |         |
           |         +-- roadIndex (1) ........... [NA] Integer32
           |         +-- roadName (2) ............ [RC] DisplayString
           |         +-- roadType (3) ............ [RC] RoadType
           |         +-- roadRTG (4) ............. [RW] Gauge32
           |         +-- roadMaxCapacity (5) ..... [RC] Gauge32
           |         +-- roadVehicleCount (6) .... [RO] Gauge32
           |         +-- roadTotalCarsPassed (7) . [RO] Counter32
           |         +-- roadAvgWaitTime (8) ..... [RO] Gauge32
           |         +-- roadCrossroadID (9) ..... [RC] Integer32
           |         +-- roadTLColor (10) ........ [RO] TrafficColor
           |         +-- roadTLTimeRemaining (11). [RO] Integer32
           |         +-- roadTLGreenDuration (12). [RO] Integer32
           |         +-- roadTLRedDuration (13) .. [RO] Integer32
           |         +-- roadRowStatus (14) ...... [RC] RowStatus
           |
           +-- roadLinkTable (5)  
                |
                +-- roadLinkEntry (1) [INDEX: linkIndex]
                     |
                     +-- linkIndex (1) ........... [NA] Integer32
                     +-- linkSourceIndex (2) ..... [RC] Integer32
                     +-- linkDestIndex (3) ....... [RC] Integer32
                     +-- linkFlowRate (4) ........ [RC] Gauge32
                     +-- linkActive (5) .......... [RC] LinkState
                     +-- linkCarsPassed (6) ...... [RO] Counter32
                     +-- linkRowStatus (7) ....... [RC] RowStatus

```

# Interações Funcionais entre os Componentes do Sistema

A arquitetura do Sistema de Gestão de Tráfego Rodoviário assenta em quatro componentes fundamentais, organizados num modelo que separa a monitorização externa da lógica central de simulação e decisão. 

Como ilustrado no diagrama de blocos abaixo, o sistema centraliza o núcleo lógico no componente **SC (Sistema Central)**, criando uma separação clara entre dois domínios de comunicação: as comunicações externas via rede e os acessos internos em memória.

<img src="image2.png" width="500">

## A. Interações Externas (Protocolo SNMPv2c)

A comunicação externa ocorre exclusivamente entre a Consola de Monitorização e Controlo (CMC) e o Sistema Central (SC) através do protocolo SNMPv2c (sem mecanismos de segurança nesta fase).

- **Monitorização (CMC → SC)**: A CMC atua como um gestor SNMP, enviando pedidos assíncronos GET (ou GETNEXT para tabelas) ao SC para ler continuamente as instâncias da MIB (ex: roadVehicleCount, tlColor, tlTimeRemaining, roadTotalCarsPassed, roadAverageWaitTime) e atualizar a sua interface de acompanhamento em quase tempo real.

- **Configuração e Controlo (CMC → SC)**: Quando o administrador introduz um comando no prompt da CMC, esta envia um pedido SET ao agente SNMP do SC para manipular instâncias específicas, nomeadamente o objeto roadRTG de uma via (injetando tráfego no sistema) ou os parâmetros algorítmicos (algoMinGreenTime, algoMaxGreenTime).

## B. Interações Internas (Acesso Direto em Memória)

Por uma questão de simplificação e eficiência, o Sistema de Simulação do Fluxo Rodoviário (SSFR) e o Sistema de Decisão (SD) estão integrados dentro do próprio processo do SC. Como tal, não utilizam SNMP para interagir com a MIB, acedendo diretamente às estruturas de dados.

- **Interação SSFR ↔ MIB**: 
  - *Leitura*: A cada ciclo de simulação, o SSFR consulta os valores de roadRTG, a cor atual dos semáforos (tlColor), as vias de destino disponíveis e a lotação das mesmas para determinar se o escoamento é possível.

  - *Escrita*: O SSFR calcula o movimento dos veículos e atualiza adequadamente os valores das instâncias `roadVehicleCount` nas vias de origem (subtraindo veículos) e nas vias de destino (adicionando veículos). Atualiza também os contadores `roadTotalCarsPassed`, `roadAverageWaitTime`, `totalVehiclesEntered`, `totalVehiclesExited` e `linkCarsPassed`.

- **Interação SD ↔ MIB**: 
  - *Leitura*: O SD acede aos dados presentes na MIB (nomeadamente a carga de tráfego, representada por roadVehicleCount) e aos parâmetros algorítmicos (algoMinGreenTime, algoMaxGreenTime) para alimentar a sua heurística de cálculo.

  - *Escrita*: O SD atualiza as instâncias tlColor (estado da cor), tlTimeRemaining, tlGreenDuration e tlRedDuration para cada um dos semáforos do sistema, operando sempre em intervalos temporais múltiplos do passo da simulação do SSFR.


