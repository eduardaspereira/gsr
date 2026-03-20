# 🧪 GUIA DE TESTES - SISTEMA GSR

## 1️⃣ TESTE RÁPIDO (30 segundos) - Verificar se tudo funciona

```bash
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
source venv/bin/activate
python3 quick_test.py
```

**O que faz:**
- Verifica imports
- Carrega config.json
- Cria MIB
- Testa 30 segundos de simulação
- Mostra se passou ✓ ou falhou ✗

**Resultado esperado:**
```
✓ Imports OK
✓ Configuration OK
✓ MIB Creation OK
✓ Simulation (30s) OK
✓ All tests passed!
```

---

## 2️⃣ TESTE COMPLETO (1 minuto) - Validação de Tudo

```bash
python3 test_complete.py
```

**O que faz:**
7 módulos de teste:
1. Importações (todas as dependências)
2. Parser de configuração
3. Criação e acesso da MIB
4. SNMP bridge (compartilhamento global)
5. Algoritmos (os 3 existem)
6. Simuladores (60 segundos de teste)
7. Visualizador (desenha mapas)

**Resultado esperado:**
```
═══════════════════════════════════════════════
      Testes de Sistema - GSR
═══════════════════════════════════════════════

✓ Teste 1: Importações
✓ Teste 2: Parser de Configuração
✓ Teste 3: MIB Objects
✓ Teste 4: SNMP Bridge
✓ Teste 5: Algoritmos
✓ Teste 6: Simuladores (60s)
✓ Teste 7: Visualizador

Resultado: 7/7 testes passaram ✓
Taxa de sucesso: 100%
```

---

## 3️⃣ TESTE INTERATIVO - Sistema Completo em Ação

### Terminal 1: Iniciar Sistema Central (SC)

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
✓ Servidor SNMP iniciado em 127.0.0.1:10161
✓ SSFR iniciado (passo = 5s)
✓ SD iniciado (ciclo = 5s)
Sistema pronto. [Ctrl+C para parar]

[Sistema roda indefinidamente...]
```

**✅ Deixa isto a rodar!**

---

### Terminal 2: Iniciar CMC (Consola de Monitorização)

```bash
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
source venv/bin/activate
python3 -m src.console
```

**Comandos para testar:**

```bash
# 1. Ver ajuda
gsr> help

# 2. Ver mapa da rede
gsr> map
    ╔═══════════════════════════════════╗
    ║    Rede de Tráfego Rodoviário    ║
    ║                                   ║
    ║    Via 1 (Entrada)  Via 2 (Ent)  ║
    ║    ════════════════ ═════════════ ║
    ║         ↓               ↓          ║
    ║         └────┬──────────┘          ║
    ║         🟢 Cruzamento 1            ║
    ║              ↓                     ║
    ║    Via 3 (Saída) ═════════════    ║
    ╚═══════════════════════════════════╝

# 3. Ver estatísticas globais
gsr> stats
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

# 4. Monitorização contínua (atualiza a cada 5s)
gsr> monitor
[Atualiza continuamente - pressiona Ctrl+C para parar]

# 5. Ver todas as vias em tabela
gsr> roads

Via 1 (Avenida Principal) [SOURCE]
  Carros: 15/100 | Espera: 8.5s | RGT: 30/min | 🟢 GREEN (22s)

Via 2 (Rua Secundária) [SOURCE]
  Carros: 5/50  | Espera: 5.2s | RGT: 10/min | 🔴 RED (48s)

Via 3 (Estrada Nacional) [SINK]
  Carros: 18/200 | Saídas: 82 | 🟢 GREEN

# 6. Mudar RGT (ritmo de geração) da Via 1
gsr> set roadRTG 1 50
✓ RGT da Via 1 alterado para 50 carros/minuto
[Vê como Via 1 fica mais cheia nos próximos passos]

# 7. Mudar Algoritmo (1, 2 ou 3)
gsr> set algorithm 2
✓ Algoritmo alterado para 2 (OccupancyHeuristic)
[Semáforos agora se adaptam à ocupação]

# 8. Sair
gsr> exit
```

---

## 4️⃣ TESTE COM CMC GRÁFICA (Nova!)

```bash
python3 cmc_grafica.py
```

**Output:**
```
════════════════════════════════════════════════════════════════════════════════════════════════════
SISTEMA DE GESTÃO DE TRÁFEGO RODOVIÁRIO (GSR)
Universidade do Minho - Mestrado em Engenharia Informática
════════════════════════════════════════════════════════════════════════════════════════════════════
[15:30:45]  Status: RUNNING  |  Algoritmo: OccupancyHeuristic
────────────────────────────────────────────────────────────────────────────────────────────────────

┌─ TOPOLOGIA DA REDE ────────────────────────────────────────────────────────────────────────┐

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
       ↓         ┼─────────┼                           ↓
       ↓         │         │                           ↓

                    VIA 3 (Estrada Nacional - SAÍDA)
                    Carros: 23 / 200  [███░░░░░░░░░░░]  11.5%
                       ↓
                     │   │   │
                  (Saem da rede)

└────────────────────────────────────────────────────────────────────────────────────────────┘

┌─ SEMÁFOROS (Traffic Lights) ──────────────────────────────────────────────────────────────┐

    Cruzamento 1

    Via 1 (Avenida Principal):
      Estado: ● GREEN | Tempo restante: 22s | Duração Verde: 40s
      RGT (entrada): 30 carros/min | Tipo: SOURCE

    Via 2 (Rua Secundária):
      Estado: ● RED   | Tempo restante: 48s | Duração Verde: 40s
      RGT (entrada): 10 carros/min | Tipo: SOURCE

└────────────────────────────────────────────────────────────────────────────────────────────┘

[Dashboard atualiza a cada 5 segundos...]
```

---

## 5️⃣ CENÁRIOS DE TESTE - Comportamento Esperado

### Cenário A: Teste de Injeção de Carros

**Passo:**
1. Inicia SC + CMC
2. `gsr> monitor` (observa 20 segundos)
3. `gsr> set roadRTG 1 50` (aumenta via 1)
4. Observa 20 segundos mais

**Resultado esperado:**
- Antes: Via 1 tem ~3-5 carros
- Depois: Via 1 tem ~10-15 carros (dobra!)
- Tempo de espera sobe

---

### Cenário B: Teste de Algoritmos

**Passo:**
1. Inicia com Algoritmo 1 (FixedCycle)
2. Observa 30 segundos
3. `gsr> set algorithm 2` (muda para OccupancyHeuristic)
4. Observa 30 segundos mais
5. `gsr> set algorithm 3` (muda para BackpressureControl)
6. Observa 30 segundos

**Resultado esperado:**
- **Alg 1:** Semáforos piscam regulares (40s + 3s)
- **Alg 2:** Tempos mudam conforme ocupação
- **Alg 3:** Mais conservador (evita engarrafamentos)

---

### Cenário C: Teste de Fluxo Completo

**Passo:**
1. Aumenta Via 1: `set roadRTG 1 60`
2. Aumenta Via 2: `set roadRTG 2 30`
3. Observa 60 segundos

**Resultado esperado:**
- Via 1 e 2 ficam mais cheias
- Semáforo alterna mais rapidamente
- Carros saem pela Via 3
- Tempo médio de espera sobe

---

## 6️⃣ VERIFICAR LOGS (Debugging)

Se algo falhar, vê os logs:

```bash
# Terminal onde roda o SC:
# [Vê mensagens como]
2026-03-20 15:30:45 - SSFR - INFO - Step 1: Injected 2 vehicles into Road 1
2026-03-20 15:30:45 - SD - INFO - Algorithm 1: Green time for Crossroad 1 = 40s
2026-03-20 15:30:50 - SSFR - INFO - Step 2: Moved 15 vehicles Road 1->3
```

---

## 7️⃣ CHECKLIST DE TESTES

- [ ] **Teste 1** - `python3 quick_test.py` passa ✓
- [ ] **Teste 2** - `python3 test_complete.py` passa ✓
- [ ] **Teste 3** - SC inicia sem erros
- [ ] **Teste 4** - CMC conecta e mostra dados
- [ ] **Teste 5** - `map` desenha topologia
- [ ] **Teste 6** - `stats` mostra números realistas
- [ ] **Teste 7** - `set roadRTG 1 50` funciona
- [ ] **Teste 8** - `set algorithm 2` funciona
- [ ] **Teste 9** - Carros aumentam em Via 1 depois de `set roadRTG 1 50`
- [ ] **Teste 10** - CMC gráfica `cmc_grafica.py` mostra dashboard

---

## 8️⃣ TROUBLESHOOTING

### Problema: "Port already in use"
```bash
# Matar processo anterior
lsof -i :10161
kill -9 <PID>
```

### Problema: "MIB not found"
```bash
# Certifica-te que SC está a rodar num terminal
# E que esperas 2-3 segundos depois de iniciar
```

### Problema: CMC mostra "erro ao conectar"
```bash
# Usa CMC gráfica que usa snmp_bridge (local):
python3 cmc_grafica.py
# Não precisa SNMP, apenas da MIB em memória
```

### Problema: "ModuleNotFoundError"
```bash
# Certifica-te que ativaste venv
source venv/bin/activate
# E que estás no diretório correto
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
```

---

## ✅ RESUMO DO TESTE COMPLETO

1. **Rápido (30s):** `python3 quick_test.py` ✓
2. **Completo (1m):** `python3 test_complete.py` ✓
3. **Interativo:** 2 terminais (SC + CMC) ✓
4. **Visual:** `python3 cmc_grafica.py` ✓

**Se tudo passar, sistema está 100% funcional! 🎉**

