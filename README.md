# Projeto GSR - Sistema de Gestão de Tráfego Rodoviário (Fase A)
Este projeto implementa um sistema de gestão de tráfego rodoviário baseado na arquitetura Internet-standard Network Management Framework (INMF). Utiliza o protocolo SNMPv2c para monitorizar e controlar o fluxo de veículos em tempo quase-real, visando a minimização dos tempos médios de espera.
## Funcionalidades Principais
- **Arquitetura de Componentes**: Divisão clara entre Sistema Central (Agente), Simulador, Decisor e Consolas (Gestores).

- **Modelo de Informação SMIv2**: Implementação de uma MIB experimental estruturada em tabelas (roadTable e roadLinkTable) para representar a rede como um grafo.

- **Controlo Inteligente (SD)**: Algoritmo que utiliza heurísticas de pressão e a funcionalidade de "Onda Verde" para antecipar pelotões de veículos.

- **Simulação Realista (SSFR)**: Passos de 5 segundos que processam o movimento físico, escoamento para sumidouros e gestão de capacidade das vias.

- **Monitorização Multi-Consola**: Inclui uma consola de gestão tabular e uma interface gráfica em ASCII com cores ANSI.

## Estrutura do Sistema 
**Sistema Central (SC)**:
- Atua como o Agente SNMPv2c (Porta 1161).
- Gere a instrumentação dinâmica da MIB baseada no ficheiro config.json.
- Sincroniza em tempo real os dados da simulação com os objetos SNMP (ex: roadVehicleCount, roadLightColor). 

**Sistema de Simulação (SSFR)**: 
- Simula a entrada de veículos via Ritmo Gerador de Tráfego (RGT).
- Calcula estatísticas de performance, como o tempo médio de espera por via.
- Gere o escoamento para fora da rede (vias sumidouro) e a ocupação máxima das vias para evitar bloqueios físicos.

**Sistema de Decisão (SD)**:
- Heurística de Pressão: Prioriza eixos com maior acumulação de veículos.
- Onda Verde: Analisa os cruzamentos adjacentes; se um pelotão está a chegar a verde de uma via anterior, o SD aumenta a "pressão virtual" para abrir o próximo sinal antecipadamente.
- Prevenção de Deadlock: O sinal não abre se a via de destino estiver com ocupação superior a 90%.
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

Terminal 2 (A Tabela / Controlo): Inicia a CMC para desenhar uma tabela com as 8 vias e ficar à espera dos teus comandos.
```Bash
python3 cmc_manager.py
```

Terminal 3 (O Mapa Gráfico): Inicia o visualizador ASCII para ver o cruzamento em tempo real.
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
Vias 1,2,3,4 tem os valores exatos do JSON  
Vias 5,6,7,8 são sumidouros e por isso têm valor 0  

```bash
iso.3.6.1.4.1.9999.1.1.2.1.4.1.0 = Gauge32: 15
                           4.2.0 = Gauge32: 12
                           4.3.0 = Gauge32: 10
                           4.4.0 = Gauge32: 18
                           4.5.0 = Gauge32: 0
                           4.6.0 = Gauge32: 0
                           4.7.0 = Gauge32: 0
                           4.8.0 = Gauge32: 0
```

#### Contagem veículos em cada via
```bash
                           6.1.0 = Gauge32: 6
                           6.2.0 = Gauge32: 1
                           6.3.0 = Gauge32: 16
                           6.4.0 = Gauge32: 23
                           6.5.0 = Gauge32: 2
                           6.6.0 = Gauge32: 2
                           6.7.0 = Gauge32: 3
                           6.8.0 = Gauge32: 3
```

#### Cor dos Semáforos
1 -- Vermelho  
2 -- Verde  

```bash
                           7.1.0 = INTEGER: 2
                           7.2.0 = INTEGER: 2
                           7.3.0 = INTEGER: 1
                           7.4.0 = INTEGER: 1
                           7.5.0 = INTEGER: 2
                           7.6.0 = INTEGER: 2
                           7.7.0 = INTEGER: 2
                           7.8.0 = INTEGER: 2
```

## Explicação dos Resultados
Ao alterar o RGT (ex: injetando muitos carros na Via 1), vai-se observar o seguinte comportamento dinâmico:  
1. **Acumulação**: No Terminal 3 (Mapa), vê-se o número de carros a subir rapidamente na Via Norte.  

2. **Reação do SD**: O Sistema de Decisão vai detetar o desequilíbrio. Vai fechar os semáforos que estavam abertos (passando primeiro por Amarelo), e vai dar luz Verde (██) ao Eixo Norte-Sul.  

3. **Escoamento**: Os carros vão começar a subtrair da entrada Norte e a aparecer nas vias de Saída (Sumidouros, que têm o ID 5, 6, 7 e 8).  

4. **Segurança**: O Eixo transversal (Este-Oeste) fica bloqueado a Vermelho durante este processo, garantindo que não há colisões e simulando o comportamento real de um cruzamento. 

## Testes de Validação
O projeto inclui uma bateria de 12 testes unitários e de integração que validam:
- Exclusão mútua e segurança.
- Prevenção de deadlocks com destinos lotados.
- Precisão matemática da injeção de veículos.
- Lógica de antecipação (Onda Verde).
- Escoamento em sumidouros.

```bash
python3 Tests.py
```
