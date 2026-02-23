# Projeto GSR - Sistema de Gestão de Tráfego Rodoviário (Fase A)
Este projeto implementa um sistema de gestão de tráfego rodoviário baseado na arquitetura Internet-standard Network Management Framework (INMF). Utiliza o protocolo SNMPv2c para monitorizar e controlar o fluxo de veículos em tempo quase-real, visando a minimização dos tempos médios de espera.

## Checklist Fase A 

1. Definição de requisitos   
- Estado: Done ✅  
- Implementação: Respeita os requisitos essenciais da arquitetura, nomeadamente a centralização do Sistema Central (SC) como agente SNMP, a injeção contínua de veículos via Ritmo Gerador de Tráfego (RGT) no SSFR, o cálculo autónomo de semáforos no SD e a monitorização externa através da Consola de Monitorização e Controlo (CMC). 
---
2. Modelo de informação e interações  
- Estado: WIP (Work in Progress)  
- Implementação: O modelo conceptual baseia-se numa representação em grafo (vias como nós, escoamentos como arestas). As interações internas ocorrem diretamente em memória no SC (onde o SSFR e o SD atualizam instâncias), ao passo que a interação externa ocorre através do protocolo SNMPv2c entre a CMC e o SC.  
--- 
3. Algoritmo inicial no SD  
- Estado: Done ✅  
- Implementação: No ficheiro sistema_decisao.py, aplicou-se uma heurística inteligente de "pressão" em filas de espera. O algoritmo conta os veículos nos eixos concorrentes (Norte-Sul e Este-Oeste) e atribui o sinal verde ao eixo com maior volume de tráfego, garantindo sempre a exclusão mútua e bloqueando transições inseguras. 
--- 
4. Mapa da rede rodoviária 
- Estado: WIP (Work in Progress)  
- Implementação: Tem-se uma rede delineada no config.json, carece de validação. Contempla artérias principais (Avenida Principal), ruas transversais e respetivos cruzamentos (1 e 2), culminando em vias do tipo "sumidouro" (IDs 97, 98 e 99) para escoamento para o exterior da zona urbana gerida.
--- 
5. Ferramentas e Linguagem 
- Estado: Done ✅
- Implementação: Escolheu-se a linguagem Python. Utilizou-se a biblioteca pysnmp em modo assíncrono (asyncio) para instanciar tanto o motor do servidor SNMP no SC como os pedidos de gestão na CMC.
--- 
6. Sintaxe do ficheiro de configuração 
- Estado: Done ✅
- Implementação: Adotou-se o formato JSON (config.json), garantindo uma sintaxe de fácil leitura humana e estruturação hierárquica ideal para o processamento de listas de vias, semáforos e capacidades no momento de arranque do sistema.
--- 
7. Interface de utilizador da CMC 
- Estado: WIP (Work in Progress)  
- Implementação: Criaram-se 2 abordagens complementares no terminal: uma tabular com uma linha de comandos para injetar pedidos SET (cmc_manager.py) e outra em ASCII art para visualização gráfica das cores e do trânsito na topologia (cmc_grafica.py).
--- 
8. Especificação da MIB e interações SNMP 
- Estado: WIP (Work in Progress)  
- Implementação: Criou-se a TRAFFIC-MGMT-MIB em sintaxe SMIv2/ASN.1 e mapearam-se nela os objetos do código (ex. roadTable). Estão estabelecidas as interações via GET (leitura periódica de roadVehicleCount e roadLightColor), GETNEXT (descoberta de vias) e SET (alteração dinâmica do roadRTG).
--- 
9. Implementação da primeira versão do SC com a instrumentação de alguns objetos da MIB (sem componente SD e SSRF) e da primeira versão básica da CMC para testar a comunicação SNMP e para verificar a correta instrumentação da MIB no SC. 
- Estado: WIP (Work in Progress)  
--- 
10. Implementação e teste da instrumentação da MIB completa no SC.
- Estado: WIP (Work in Progress)  
- Implementação: No ficheiro sc_agent.py, inicializa-se o motor SNMP na porta UDP 1161, regista-se a comunidade public e exporta-se dinamicamente todos os OIDs lidos do config.json para o construtor da MIB utilizando classes como MibScalarInstance.
--- 
11. Componente SSFR integrado no SC 
- Estado: WIP (Work in Progress)  
- Implementação: O ficheiro ssfr.py corre de forma cíclica dentro do SC. A cada passo temporal, injeta veículos de acordo com o RGT e calcula a passagem de X veículos por minuto para as vias de destino, subtraindo na origem e somando no destino se houver espaço.
--- 
12. Componente SD integrado no SC 
- Estado: WIP (Work in Progress)  
- Implementação: O módulo sistema_decisao.py é chamado na mesma thread de simulação do SC, atualizando os tempos restantes e os estados (1, 2 ou 3) nos objetos em memória, que por sua vez se refletem automaticamente na MIB exportada por SNMP.
--- 
13. Melhorias finais na CMC 
- Estado: 
--- 
14. Melhorias finais no SD 
- Estado: 



## Funcionalidades Principais
- **Arquitetura de Componentes**: Divisão clara entre Sistema Central (Agente), Simulador, Decisor e Consolas (Gestores).

- **Modelo de Informação SMIv2**: Implementação de uma MIB experimental estruturada em tabelas (roadTable e roadLinkTable) para representar a rede como um grafo.

- **Controlo Inteligente (SD)**: Heurística simples de pressão que prioriza o eixo com mais veículos.

- **Simulação Realista (SSFR)**: Passos de 5 segundos que processam o movimento físico, escoamento para sumidouros e gestão de capacidade das vias.

- **Monitorização Multi-Consola**: Inclui uma consola de gestão tabular e uma interface gráfica em ASCII com cores ANSI.

## Estrutura do Sistema 
**Sistema Central (SC)**:
- Atua como o Agente SNMPv2c (Porta 1161).
- Gere a instrumentação dinâmica da MIB baseada no ficheiro config.json.
- Sincroniza em tempo real os dados da simulação com os objetos SNMP (ex: roadVehicleCount, roadLightColor). 

**Sistema de Simulação (SSFR)**: 
- Simula a entrada de veículos via Ritmo Gerador de Tráfego (RGT).
- Gere o escoamento para fora da rede (vias sumidouro) e a ocupação máxima das vias para evitar bloqueios físicos.

**Sistema de Decisão (SD)**:
- Heurística de Pressão: Prioriza eixos com maior acumulação de veículos.
- Segurança: Garante exclusão mútua total e respeita o tempo de amarelo fixo.

**Consola de Monitorização e Controlo (CMC)**:
- Descoberta Dinâmica: Utiliza GETNEXT (SNMP Walk) para descobrir automaticamente os IDs das vias ativas sem configuração prévia.
- Controlo Ativo: Permite ao administrador alterar os RGTs via comandos SET SNMP.
- Visualização ANSI: O mapa gráfico ilustra a topologia e o estado dos semáforos em tempo real usando blocos de cores.


## Compilar MIB
Antes da primeira execução, é obrigatório compilar o ficheiro de texto da MIB (ProjetoGSR.mib) para um formato Python que o agente consiga ler:  
```bash
mibdump --mib-source=file:///usr/share/snmp/mibs --mib-source=https://mibs.pysnmp.com/asn1/@mib@ --mib-source=file://. --destination-directory=. --destination-format=pysnmp ProjetoGSR.mib
```

## Demonstração
Terminal 1 (O Servidor): Inicia o Sistema Central para carregar o mapa do config.json e ficar à escuta na porta 1161.  
```Bash
python3 sc_agent.py
```

Terminal 2 (A Tabela / Controlo): Inicia a CMC para desenhar uma tabela com as 10 vias do config.json (1, 2, 3, 4, 97, 98, 99, 10, 11, 12) e ficar à espera dos teus comandos.
```Bash
python3 cmc_manager.py
```

Terminal 3 (O Mapa Gráfico): Inicia o visualizador ASCII para ver apenas os cruzamentos 1 e 2 (vias 1, 2, 3, 4 e sumidouros 97, 98, 99) em tempo real.
```Bash
python3 cmc_grafica.py
```

## Comandos a Usar dentro da CMC (Terminal 2)
Pode-se alterar o ritmo a que os carros entram na rede (RGT) a qualquer momento usando a sintaxe set <ID_DA_VIA> <NOVO_RGT>.
 - Exemplo para simular a hora de ponta a Norte (Via 1 com 60 carros/min): set 1 60  
 - Exemplo para cortar o trânsito a Este (Via 3): set 3 0  

## Teste de Conformidade SNMP 
Para provar que o  Agente responde a ferramentas standard de mercado, corre um SNMP Walk completo à nossa árvore de gestão:
```bash
snmpwalk -v2c -c public 127.0.0.1:1161 1.3.6.1.4.1.9999
```

### Explicação Teste de Conformidade SNMP 
#### Ritmo Gerador de Tráfego
As vias com RGT definido no config.json devolvem esse valor, e as vias sem RGT (ou sumidouros) devolvem 0. IDs esperados: 1, 2, 3, 4, 97, 98, 99, 10, 11, 12.

```bash
iso.3.6.1.4.1.9999.1.1.2.1.4.1.0 = Gauge32: 20
                           4.2.0 = Gauge32: 0
                           4.3.0 = Gauge32: 5
                           4.4.0 = Gauge32: 5
                           4.10.0 = Gauge32: 0
                           4.11.0 = Gauge32: 0
                           4.12.0 = Gauge32: 0
                           4.97.0 = Gauge32: 0
                           4.98.0 = Gauge32: 0
                           4.99.0 = Gauge32: 0
```

#### Contagem veículos em cada via
Os valores variam com a simulação, mas os IDs devolvidos devem corresponder às vias do config.json.

```bash
iso.3.6.1.4.1.9999.1.1.2.1.6.1.0 = Gauge32: 0
                           6.2.0 = Gauge32: 0
                           6.3.0 = Gauge32: 0
                           6.4.0 = Gauge32: 0
                           6.10.0 = Gauge32: 60
                           6.11.0 = Gauge32: 0
                           6.12.0 = Gauge32: 0
                           6.97.0 = Gauge32: 0
                           6.98.0 = Gauge32: 0
                           6.99.0 = Gauge32: 0
```

#### Cor dos Semáforos
1 -- Vermelho  
2 -- Verde  
3 -- Amarelo  

```bash
iso.3.6.1.4.1.9999.1.1.2.1.7.1.0 = INTEGER: 1
                           7.2.0 = INTEGER: 1
                           7.3.0 = INTEGER: 1
                           7.4.0 = INTEGER: 1
                           7.10.0 = INTEGER: 2
```

## Testes de Validação
O projeto inclui uma bateria de 6 testes unitários e de integração que validam:
- Exclusão mútua e segurança.
- Precisão matemática da injeção de veículos.
- Escoamento em sumidouros.

```bash
python3 Tests.py
```