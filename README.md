
# Projeto GSR - Sistema de Gestão de Tráfego Rodoviário (Fase A)
Este projeto implementa um protótipo de gestão de tráfego rodoviário baseado na arquitetura INMF utilizando o protocolo SNMPv2c. O objetivo principal é gerir o fluxo de veículos num cruzamento urbano, minimizando os tempos globais de espera.

## Lógica do Sistema
O projeto está dividido em quatro componentes principais:  
 - Sistema Central (SC) + MIB: Atua como o Agente SNMP (sc_agent.py). Mantém a base de dados (roadTable) em memória com toda a informação do cruzamento (veículos, cor dos semáforos, ritmos).  

 - Sistema de Simulação (SSFR): Corre dentro do SC (ssfr.py). Injeta veículos nas vias a um Ritmo Gerador de Tráfego (RGT) e move os carros pelos semáforos a cada ciclo de 5 segundos.  

 - Sistema de Decisão (SD): Corre dentro do SC (sistema_decisao.py). Utiliza uma Heurística de Exclusão Mútua. Em vez de olhar para vias isoladas, o SD divide o cruzamento em duas Fases (Eixo Norte-Sul e Eixo Este-Oeste). O sistema avalia qual dos eixos tem a maior fila de espera total e dá-lhe prioridade (Sinal Verde), trancando o eixo transversal (Sinal Vermelho) para evitar colisões mortais no centro. Além disso, previne deadlocks verificando se a via de destino tem capacidade antes de abrir o sinal.  

 - Consola de Monitorização e Controlo (CMC): Atua como o Gestor SNMP (cmc_manager.py e cmc_grafica.py). Descobre dinamicamente a topologia da rede através de um SNMP Walk e permite alterar os RGTs em tempo real .  

## Compilar MIB
Antes da primeira execução, é obrigatório compilar o ficheiro de texto da MIB (ProjetoGSR.mib) para um formato Python que o agente consiga ler. Na diretoria do projeto, para gerar o ficheiro TRAFFIC-MGMT-MIB.py, corre:  
```bash
mibdump --mib-source=file:///usr/share/snmp/mibs --mib-source=https://mibs.pysnmp.com/asn1/@mib@ --mib-source=file://. --destination-directory=. --destination-format=pysnmp ProjetoGSR.mib
```
## Demonstração
Terminal 1 (O Servidor): Inicia o Sistema Central. Ele vai carregar o mapa do config.json e ficar à escuta na porta 1161.  
```Bash
python3 sc_agent.py
```

Terminal 2 (A Tabela / Controlo): Inicia a CMC. Ela vai desenhar uma tabela com as 8 vias e ficar à espera dos teus comandos.
```Bash
python3 cmc_manager.py
```

Terminal 3 (O Mapa Gráfico): Inicia o visualizador ASCII para veres o cruzamento em tempo real.
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