# Sistema Central de Gestão de Tráfego Rodoviário - Guia de Início Rápido

## 📦 Estrutura do Projeto

```
src/
├── __init__.py              # Pacote Python
├── central_system.py        # Orquestrador principal (entry point)
├── config_parser.py         # Parser e validador de config.json
├── mib_objects.py           # Estrutura da MIB em memória
├── snmp_server.py           # Servidor SNMP SNMPv2c
├── snmp_client.py           # Cliente SNMP (para testes)
├── ssfr.py                  # 🚗 Simulador de Fluxo Rodoviário
└── decision_system.py       # 🚦 Controlo de Semáforos

config.json                 # Configuração da rede
requirements.txt           # Dependências Python
venv/                      # Ambiente virtual Python
quick_test.py              # Script de teste rápido
test_simulation.py         # Script de teste detalhado
```

## 🚀 Quickstart

### 1. Setup Inicial (primeira vez)
```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Executar Simulação
```bash
# Ativar venv se necessário
source venv/bin/activate

# Opção A: Teste rápido (30 segundos)
python3 quick_test.py

# Opção B: Sistema completo com SNMP (Ctrl+C para parar)
python3 -m src.central_system -H 127.0.0.1 -p 10161

# Opção C: Teste detalhado com estatísticas
python3 test_simulation.py
```

### 3. Testar com snmpget (se instalado)
```bash
# Terminal diferente
snmpget -v2c -c public 127.0.0.1:10161 1.3.6.1.3.2026.1.1.4
```

## 📋 O Que Está Implementado

### ✅ Fase A - Especificação (Completa)
- [x] Requisitos funcionais detalhados
- [x] Modelo de informação (MIB)
- [x] Investigação de algoritmos
- [x] Mapa de rede rodoviária

### ✅ Fase B - Implementação (Em Progresso)

#### Componente 1: Sistema Central (SC)
- [x] Parser JSON com validação robusta
- [x] MIB em memória com thread-safety
- [x] Servidor SNMP SNMPv2c básico
- [x] Orquestrador integrado

#### Componente 2: SSFR (Simulação Fluxo)
- [x] Injeção de veículos respeitando RGT
- [x] Movimento entre vias respeitando semáforos
- [x] Cálculo de tempos de espera
- [x] Contadores e métricas
- [x] Thread de simulação a 5 segundos configuráveis

#### Componente 3: SD (Decisão de Semáforos)
- [x] Algoritmo FixedCycle (baseline)
- [x] Algoritmo OccupancyHeuristic
- [x] Algoritmo BackpressureControl
- [x] Thread independente de decisões
- [x] Possibilidade de trocar algoritmo em runtime

#### Componente 4: CMC (Consola)
- [ ] Cliente SNMP funcional
- [ ] Interface interativa
- [ ] Comandos de controlo (set RGT, mudar algoritmo)

---

## 🧪 Output do Teste Rápido

```
======================================================================
TESTE RÁPIDO: SSFR + DecisionSystem
======================================================================

Iniciado. Coletando dados por 30 segundos...

----------------------------------------------------------------------
T= 15s | Veículos= 2 | Entrada= 6 | Saída= 4 | Espera med=  5.0s
T= 20s | Veículos= 0 | Entrada= 8 | Saída= 8 | Espera med=  0.0s
T= 30s | Veículos= 0 | Entrada=12 | Saída=12 | Espera med=  0.0s
----------------------------------------------------------------------

✓ Teste concluído com sucesso!
======================================================================
```

---

## 📋 Configuração (config.json)

```json
{
  "trafficGeneral": {
    "simStepDuration": 5,           // Passo de simulação (segundos)
    "algoYellowTime": 3,            // Tempo fixo de amarelo
    "algoMinGreenTime": 15,         // Verde mínimo
    "algoMaxGreenTime": 60,         // Verde máximo
    "currentAlgorithm": 1           // 1=FixedCycle, 2=Occupancy, 3=Backpressure
  },
  "crossroads": [
    { "crossroadIndex": 1, "crossroadMode": 1 }
  ],
  "roads": [
    {
      "roadIndex": 1,
      "roadName": "Avenida Principal (Entrada)",
      "roadType": 3,                // 1=Normal, 2=Sink, 3=Source
      "roadRTG": 30,                // Ritmo Gerador (veículos/minuto)
      "roadMaxCapacity": 100,
      "roadVehicleCount": 20,
      "roadCrossroadID": 1
    }
  ],
  "roadLinks": [
    {
      "linkIndex": 1,
      "linkSourceIndex": 1,
      "linkDestIndex": 3
    }
  ]
}
```

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────┐
│      Sistema Central de Gestão de Tráfego      │
└─────────────────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
  ┌─────┐        ┌─────────┐    ┌────────┐
  │ MIB │        │ SNMP    │    │  SSFR  │
  │     │        │ Server  │    │        │
  └─────┘        └─────────┘    └────────┘
      │              │              │
      └──────────────┼──────────────┘
                     │
              Thread-Safe
             (RLock MIB)
                     │
      ┌──────────────┴──────────────┐
      │                             │
  ┌───────────┐          ┌──────────────┐
  │    CMC    │          │ DecisionSystem
  │ (Futuro)  │          │  (Algoritmos)
  └───────────┘          └──────────────┘
       │                        │
       └────────────┬───────────┘
                    │
           Controlo de Semáforos
           e Simulação de Tráfego
```

---

## 📝 MIB (OIDs disponíveis)

### trafficGeneral (1.3.6.1.3.2026.1.1.X)
```
.1  simStatus                (RW)  Estado: stopped(1), running(2), paused(3)
.2  simStepDuration          (RW)  Duração do passo (segundos)
.3  simElapsedSeconds        (RO)  Tempo total decorrido
.4  globalVehicleCount       (RO)  Total de veículos na rede
.5  globalAvgWaitTime        (RO)  Tempo médio de espera global
.6  totalEnteredVehicles     (RO)  Total acumulado de entradas
.7  totalExitedVehicles      (RO)  Total acumulado de saídas
.8  algoMinGreenTime         (RW)  Verde mínimo (segundos)
.9  algoMaxGreenTime         (RW)  Verde máximo (segundos)
.10 algoYellowTime           (RO)  Amarelo (segundos)
.11 currentAlgorithm         (RW)  Algoritmo: 1=Fixed, 2=Occupancy, 3=Backpressure
```

### roadTable (1.3.6.1.3.2026.1.3.X)
```
[roadIndex]
├── .2 roadName              (RC)  Nome legível
├── .3 roadType              (RC)  Tipo: normal(1), sink(2), source(3)
├── .4 roadRTG               (RW)  Ritmo Gerador (veíc/min)
├── .5 roadMaxCapacity       (RC)  Capacidade máxima
├── .6 roadVehicleCount      (RO)  Veículos atualmente
├── .7 roadTotalPassedCars   (RO)  Total passed (acumulado)
├── .8 roadAvgWaitTime       (RO)  Tempo médio espera
├── .10 roadTLColor          (RO)  Semáforo: red(1), yellow(2), green(3)
├── .11 roadTLTimeRemaining  (RO)  Segundos até mudar cor
└── .12 roadTLGreenDuration  (RO)  Duração do verde atribuído
```

---

## 🎯 Algoritmos Disponíveis

### 1. FixedCycle (currentAlgorithm=1)
- Semáforos alternam com tempos fixos
- Baseline: ignora tráfego real
- Determinístico e simples para testes

### 2. OccupancyHeuristic (currentAlgorithm=2)
- Tempo GREEN proporcional ao número de veículos
- Mais responsivo que FixedCycle
- Risco: "starvation" em vias com pouco tráfego

### 3. BackpressureControl (currentAlgorithm=3)
- Verifica espaço em vias destino
- Se destino cheio → RED (evita backup)
- Melhor: Evita efeito dominó de congestionamento
- Recomendado para redes balanceadas

---

## 🧪 Testes Incluídos

### `quick_test.py` - Teste Rápido
```bash
python3 quick_test.py
# Simula 30 segundos, mostra estatísticas a cada 10s
```

### `test_simulation.py` - Teste Detalhado
```bash
python3 test_simulation.py
# Simula com output detalhado, status cada 5s
```

### Testes Manuais
```bash
# Iniciar servidor e deixar rodando
python3 -m src.central_system -H 127.0.0.1 -p 10161

# Em outro terminal, testar com snmpget
snmpget -v2c -c public 127.0.0.1:10161 1.3.6.1.3.2026.1.1.4
```

---

## 📦 Dependências

- **pysnmp**: 7.1.22 - Cliente/servidor SNMP
- **pyasn1**: 0.4.8 - Codificação ASN.1

```bash
# Instalar
pip install -r requirements.txt
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'src'"
```bash
cd /home/goncalo/gsr/gsr
source venv/bin/activate
python3 quick_test.py
```

### "Address already in use"
```bash
# Mudar porta
python3 -m src.central_system -p 10162

# Ou matar processo anterior
lsof -i :10161
kill -9 <PID>
```

### "Config file not found"
```bash
# config.json deve estar no diretório de trabalho
cd /home/goncalo/gsr/gsr
python3 quick_test.py
```

### Veículos não se movem
```
Verificar:
1. Semáforo está GREEN? (Check roadTLColor)
2. Há espaço na via destino? (Check roadVehicleCount < capacity)
3. Há ligações? (Check roadLinks na config)
```

---

## 📚 Referências

- [RFC 1157 - SNMP](https://tools.ietf.org/html/rfc1157) 
- [RFC 1441 - SNMPv3](https://tools.ietf.org/html/rfc1441)
- [pysnmp Documentation](https://pysnmp.readthedocs.io/)

---

## 🗺️ Próximas Etapas

### CMC (Consola de Monitorização)
- [ ] Completar SNMP client com GET/SET
- [ ] Interface interativa
- [ ] Tabelas formatadas
- [ ] Comandos (monitor, set, algo, status)

### Otimizações
- [ ] Usar deque em vez de list para veículos
- [ ] Cache OID mappings
- [ ] Batch updates na MIB

### Testes Extensivos
- [ ] Cenários de congestionamento
- [ ] Comparação de algoritmos
- [ ] Stress test (1000+ veículos)

---

**Última actualização**: 20 Março 2026  
**Status**: Fase B - Simulação Funcional ✅, Próximo: CMC  
**Versão**: 0.2.0
