# 🧪 GUIA DE TESTES - SISTEMA GSR
## Como Testar Completo com Exemplos Reais

---

## ⚡ TESTE 1: RÁPIDO (30 segundos) - ✅ RECOMENDADO

```bash
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
source venv/bin/activate
python3 quick_test.py
```

### Resultado Esperado:
```
======================================================================
TESTE RÁPIDO: SSFR + DecisionSystem
======================================================================

✓ Configuração carregada
✓ MIB inicializada
✓ Servidor SNMP inicializado
✓ SSFR iniciado
✓ DecisionSystem iniciado

----------------------------------------------------------------------
T= 10s | Veículos= 2 | Entrada= 4 | Saída= 4 | Espera med=  5.0s
T= 20s | Veículos= 4 | Entrada= 8 | Saída= 6 | Espera med=  5.0s
T= 30s | Veículos= 2 | Entrada=12 | Saída=10 | Espera med=  5.0s
----------------------------------------------------------------------

✓ Teste concluído com sucesso!
======================================================================
```

**O que valida:**
- ✅ Todas as dependências funcionam
- ✅ Config.json carrega corretamente
- ✅ MIB cria-se sem erros
- ✅ SSFR injeta e move carros
- ✅ SD calcula semáforos
- ✅ Números mudam em tempo real

---

## 🖥️ TESTE 2: INTERATIVO (Manual) - ✅ COMPLETO

### Terminal 1: Inicia Sistema Central

```bash
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
source venv/bin/activate
python3 -m src.central_system -H 127.0.0.1 -p 10161
```

**Output esperado:**
```
=== Sistema Central de Gestão de Tráfego Inicializado ===
Carregando configuração de config.json...
✓ Configuração carregada e validada com sucesso
  - Vias: 3
  - Cruzamentos: 1
  - Ligações: 2
✓ MIB inicializada com sucesso
✓ Servidor SNMP inicializado em 127.0.0.1:10161
✓ SSFR (Traffic Flow Simulator) iniciado
✓ DecisionSystem iniciado com algoritmo FIXED_CYCLE

=== Sistema Central Pronto ===
[Sistema aguarda... deixa a rodar]
```

**Deixa isto a rodar num terminal!** 🟢

---

### Terminal 2: Inicia CMC (Consola)

```bash
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
source venv/bin/activate
python3 -m src.console
```

**Agora podes testar comandos:**

#### 2.1 Ver Ajuda
```
gsr> help
```

#### 2.2 Ver Mapa da Rede
```
gsr> map
```

Resultado:
```
╔═══════════════════════════════════════╗
║    Rede de Tráfego Rodoviário        ║
║                                       ║
║    Via 1 (Entrada)  Via 2 (Ent)      ║
║    ════════════════ ═════════════    ║
║         ↓               ↓              ║
║         └────┬──────────┘              ║
║         🟢 Cruzamento 1                ║
║              ↓                        ║
║    Via 3 (Saída) ═════════════       ║
╚═══════════════════════════════════════╝
```

#### 2.3 Ver Estatísticas Globais
```
gsr> stats
```

Resultado:
```
╔══════════════════════════════════════════════╗
║ ESTATÍSTICAS GLOBAIS                         ║
╠══════════════════════════════════════════════╣
║ Status: RUNNING                              ║
║ Tempo Decorrido: 45 segundos                 ║
║ Carros na Rede: 38                           ║
║ Tempo Médio Espera: 11.2 segundos            ║
║ Total Carros Entrados: 120                   ║
║ Total Carros Saídos: 82                      ║
║ Algoritmo Atual: 1 (FixedCycle)             ║
╚══════════════════════════════════════════════╝
```

#### 2.4 Monitorização em Tempo Real (atualiza a cada 5s)
```
gsr> monitor
```

Saida atualiza continuamente... pressiona `Ctrl+C` para parar.

#### 2.5 Ver Todas as Vias em Tabela
```
gsr> roads
```

Resultado:
```
Via 1 (Avenida Principal) [SOURCE]
  Carros: 15/100 | Espera: 8.5s | RGT: 30/min | 🟢 GREEN (22s)

Via 2 (Rua Secundária) [SOURCE]
  Carros: 5/50  | Espera: 5.2s | RGT: 10/min | 🔴 RED (48s)

Via 3 (Estrada Nacional) [SINK]
  Carros: 18/200 | Saídas: 82 | 🟢 GREEN
```

#### 2.6 Mudar RGT (ritmo de geração)
```
gsr> set roadRTG 1 50
```

Output:
```
✓ RGT da Via 1 alterado para 50 carros/minuto
```

**Agora via `monitor` para observar Via 1 ficar mais cheia!**

#### 2.7 Mudar Algoritmo
```
gsr> set algorithm 2
```

Output:
```
✓ Algoritmo alterado para 2 (OccupancyHeuristic)
```

**Agora os semáforos se comportam diferente!**

---

## 📊 TESTE 3: COMPORTAMENTO OBSERVÁVEL

### Cenário: Aumento de Tráfego

1. **Estado inicial** (30 segundos):
   ```
   gsr> monitor
   ```
   Observa valores base:
   - Via 1: ~3-5 carros
   - Via 2: ~1-2 carros
   - Espera média: ~5 segundos

2. **Aumenta Via 1**:
   ```
   gsr> set roadRTG 1 50
   ```

3. **Observe novamente** (30 segundos):
   ```
   gsr> monitor
   ```
   Resultado esperado:
   - Via 1: ~10-15 carros (DOBROU!)
   - Espera média: ~15-20 segundos (AUMENTOU!)

---

### Cenário: Teste de Algoritmos

**Algoritmo 1: FixedCycle** (padrão)
```
gsr> set algorithm 1
gsr> monitor
# Semáforos piscam regularmente: 40s verde, 3s amarelo, 40s vermelho
```

**Algoritmo 2: OccupancyHeuristic**
```
gsr> set algorithm 2
gsr> monitor
# Semáforos adaptam tempo verde à ocupação
# Se Via 1 tem mais carros, fica verde mais tempo
```

**Algoritmo 3: BackpressureControl**
```
gsr> set algorithm 3
gsr> monitor
# Semáforos só abrem se destino tem espaço
# Mais conservador, evita engarrafamentos
```

---

## 🎨 TESTE 4: CMC GRÁFICA (Nova!)

```bash
python3 cmc_grafica.py
```

Mostra um **dashboard ASCII dinâmico** que atualiza a cada 5 segundos:

```
════════════════════════════════════════════════════════════════════════════════════════════════════
SISTEMA DE GESTÃO DE TRÁFEGO RODOVIÁRIO (GSR)
Universidade do Minho - Mestrado em Engenharia Informática
════════════════════════════════════════════════════════════════════════════════════════════════════
[15:30:45]  Status: RUNNING  |  Algoritmo: OccupancyHeuristic
────────────────────────────────────────────────────────────────────────────────────────────────────

┌─ TOPOLOGIA DA REDE ─────────────────────────────────────────────────────────────────────────────┐

    VIA 1 (Avenida Principal - ENTRADA)         VIA 2 (Rua Secundária - ENTRADA)
    Carros: 18 / 100  [████░░░░░░░░░░░]  18.0% Carros: 5 / 50  [██░░░░░░░░░░░░░]   10.0%
       ↓                                               ↓
       ●  🟢                                            ●  🔴
       │                                               │
       │         ╔════════════════╗                    │
       │         ║   CRUZAMENTO   ║                    │
       │         ║      (ID: 1)   ║                    │
       │         ╚════════════════╝                    │
       ↓         │         │                           ↓

                    VIA 3 (Estrada Nacional - SAÍDA)
                    Carros: 23 / 200  [███░░░░░░░░░░░]  11.5%
```

---

## ✅ CHECKLIST DE TESTES

Marca com ✓ conforme testa:

```
Teste Rápido (30s):
  [ ] python3 quick_test.py passa ✓

Teste Interativo:
  [ ] Terminal 1: python3 -m src.central_system inicia
  [ ] Terminal 2: python3 -m src.console conecta
  [ ] gsr> map desenha topologia
  [ ] gsr> stats mostra números
  [ ] gsr> monitor atualiza continuamente

Teste de Comportamento:
  [ ] gsr> set roadRTG 1 50 aumenta Via 1
  [ ] Observa Via 1 ficar mais cheia nos próximos ciclos
  [ ] gsr> set algorithm 2 muda algoritmo
  [ ] Observa semáforos comportarem-se diferente

Teste Gráfico:
  [ ] python3 cmc_grafica.py mostra dashboard
  [ ] Dashboard atualiza a cada 5 segundos
```

---

## 🐛 TROUBLESHOOTING

### "Port already in use"
```bash
# Ver o que está a usar a porta
lsof -i :10161

# Matar o processo
kill -9 <PID>

# Tentar de novo
python3 -m src.central_system
```

### "MIB not found" na CMC
```bash
# Certifica-te que:
# 1. SC está a rodar (Terminal 1)
# 2. Espera 2-3 segundos depois de iniciar
# 3. Depois abre CMC (Terminal 2)
```

### "ModuleNotFoundError"
```bash
# Ativa venv primeiro
source venv/bin/activate

# Depois testa
python3 quick_test.py
```

### CMC não consegue conectar
```bash
# Tenta a versão gráfica (usa local snmp_bridge)
python3 cmc_grafica.py
# Não precisa SNMP, só da MIB em memória
```

---

## 📈 MÉTRICAS ESPERADAS

Se o sistema está funcional, observarás:

| Métrica | Valor Esperado | Quando |
|---------|---|---|
| Carros na rede | 0-50 | Sempre |
| Tempo médio espera | 5-20s | Conforme tráfego |
| Taxa de entrada | ~2-4 carros/passo | A cada 5s |
| Taxa de saída | ~2-4 carros/passo | A cada 5s |
| Semáforos | 🟢/🟡/🔴 piscando | A cada 40-50s |

---

## 🎯 CONCLUSÃO

**Sistema é considerado Funcional se:**

✅ `quick_test.py` passa com sucesso
✅ SC inicia sem erros
✅ CMC conecta e mostra dados
✅ Carros aumentam/diminuem conforme RGT
✅ Semáforos mudam de cor
✅ Tempo médio de espera é realista

**Se tudo isto passou, sistema está **100% pronto para entrega**! 🎉**

