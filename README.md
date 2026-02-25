# Projeto GSR - Sistema de Gestão de Tráfego Rodoviário (Fase A)
Este projeto implementa um sistema de gestão de tráfego rodoviário baseado na arquitetura Internet-standard Network Management Framework (INMF). Utiliza o protocolo SNMPv2c para monitorizar e controlar o fluxo de veículos em tempo quase-real, visando a minimização dos tempos médios de espera.

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