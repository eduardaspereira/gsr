# Modelo de Informação

```
iso(1) . org(3) . dod(6) . internet(1) . private(4) . enterprises(1)  
 └── minhouniversity(9999)   
      └── trafficSystem(1)  
           ├── trafficGeneral(1)
           │    ├── simStatus(1)         INTEGER (read-write)
           │    └── simStepDuration(2)   INTEGER (read-write)
           │
           ├── roadTable(2) [INDEX { roadIndex }]  
           │    └── roadEntry(1)  
           │         ├── roadIndex(1)         INTEGER (ID da via - not-accessible)  
           │         ├── roadName(2)          OCTET STRING (read-only)  
           │         ├── roadRGT(3)           GAUGE32 (read-write)  
           │         ├── roadVehicleCount(4)  GAUGE32 (read-only)  
           │         ├── roadLightColor(5)    INTEGER { green(1), yellow(2), red(3) } (read-only)  
           │         └── roadTimeRemaining(6) INTEGER (read-only)
           │
           └── roadLinkTable(3) [INDEX { roadIndex, linkDestIndex }]
                └── roadLinkEntry(1)
                     ├── linkDestIndex(1)     INTEGER (ID via destino - not-accessible)
                     └── linkFlowRate(2)      GAUGE32 (read-write)
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


