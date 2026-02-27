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
           |    +-- simStatus (1) .............. [RW] SimOperStatus {running(1), stopped(2), reset(3)}
           |    +-- simStepDuration (2) ........ [RW] Integer32 (1..60) [sec]
           |    +-- globalVehicleCount (3) ..... [RO] Gauge32
           |    +-- algoMinGreenTime (4) ....... [RW] Integer32 (5..120) [sec]
           |    +-- algoYellowTime (5) ......... [RO] Integer32 (1..10) [sec]
           |
           +-- roadTable (2)
           |    |
           |    +-- roadEntry (1)  [INDEX: roadIndex]
           |         |
           |         +-- roadIndex (1) ........... [NA] Integer32 (1..65535)
           |         +-- roadName (2) ............ [RC] DisplayString
           |         +-- roadType (3) ............ [RC] RoadType {normal(1), sink(2), source(3)}
           |         +-- roadRTG (4) ............. [RC] Gauge32
           |         +-- roadMaxCapacity (5) ..... [RC] Gauge32
           |         +-- roadVehicleCount (6) .... [RO] Gauge32
           |         +-- roadLightColor (7) ...... [RO] TrafficColor {red(1), green(2), yellow(3)}
           |         +-- roadTimeRemaining (8) ... [RO] Integer32 [sec]
           |         +-- roadTotalCarsPassed (9) . [RO] Counter32
           |         +-- roadAverageWaitTime (10)  [RO] Gauge32 [sec]
           |         +-- roadRowStatus (11) ...... [RC] RowStatus
           |
           +-- roadLinkTable (3)
                |
                +-- roadLinkEntry (1)  [INDEX: roadIndex, linkDestIndex]
                     |
                     +-- linkDestIndex (1) ....... [NA] Integer32 (1..65535)
                     +-- linkFlowRate (2) ........ [RC] Gauge32
                     +-- linkActive (3) .......... [RC] LinkState {active(1), inactive(2)}
                     +-- linkRowStatus (4) ....... [RC] RowStatus
```

# Interações Funcionais entre os Componentes do Sistema

A arquitetura do Sistema de Gestão de Tráfego Rodoviário assenta em quatro componentes fundamentais, organizados num modelo que separa a monitorização externa da lógica central de simulação e decisão. 

Como ilustrado no diagrama de blocos abaixo, o sistema centraliza o núcleo lógico no componente **SC (Sistema Central)**, criando uma separação clara entre dois domínios de comunicação: as comunicações externas via rede e os acessos internos em memória.

<img src="image2.png" width="500">

## A. Interações Externas (Protocolo SNMPv2c)

A comunicação externa ocorre exclusivamente entre a Consola de Monitorização e Controlo (CMC) e o Sistema Central (SC) através do protocolo SNMPv2c (sem mecanismos de segurança nesta fase).

- **Monitorização (CMC → SC)**: A CMC atua como um gestor SNMP, enviando pedidos assíncronos GET (ou GETNEXT para tabelas) ao SC para ler continuamente as instâncias da MIB (ex: roadVehicleCount, roadLightColor, roadTimeRemaining) e atualizar a sua interface de acompanhamento em quase tempo real.

- **Configuração e Controlo (CMC → SC)**: Quando o administrador introduz um comando no prompt da CMC, esta envia um pedido SET ao agente SNMP do SC para manipular instâncias específicas, nomeadamente o objeto roadRGT de uma via, injetando tráfego no sistema.

## B. Interações Internas (Acesso Direto em Memória)

Por uma questão de simplificação e eficiência, o Sistema de Simulação do Fluxo Rodoviário (SSFR) e o Sistema de Decisão (SD) estão integrados dentro do próprio processo do SC. Como tal, não utilizam SNMP para interagir com a MIB, acedendo diretamente às estruturas de dados.

- **Interação SSFR ↔ MIB**: 
  - *Leitura*: A cada ciclo de simulação, o SSFR consulta os valores de roadRGT, a cor atual dos semáforos (roadLightColor), as vias de destino disponíveis e a lotação das mesmas para determinar se o escoamento é possível.

  - *Escrita*: O SSFR calcula o movimento dos veículos e atualiza adequadamente os valores das instâncias `roadVehicleCount` nas vias de origem (subtraindo veículos) e nas vias de destino (adicionando veículos).

- **Interação SD ↔ MIB**: 
  - *Leitura*: O SD acede aos dados presentes na MIB (nomeadamente a carga de tráfego, representada por roadVehicleCount) para alimentar a sua heurística de cálculo.

  - *Escrita*: O SD atualiza as instâncias roadLightColor (estado da cor) e roadTimeRemaining para cada um dos semáforos do sistema, operando sempre em intervalos temporais múltiplos do passo da simulação do SSFR.


