# 🚀 COMO TESTAR AGORA - PASSO A PASSO

## 1️⃣ TERMINAL 1 - Sistema Central

Abre **Terminal 1** e copia:

```bash
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
source venv/bin/activate
python3 -m src.central_system -H 127.0.0.1 -p 10161
```

**Espera pelo output:**
```
=== Sistema Central de Gestão de Tráfego Inicializado ===
✓ Configuração carregada
✓ MIB inicializada
✓ Servidor SNMP iniciado
✓ SSFR iniciado
✓ DecisionSystem iniciado
=== Sistema Central Pronto ===
```

✅ **Deixa isto a rodar!** Não feches este terminal.

---

## 2️⃣ TERMINAL 2 - Consola (CMC)

Abre **Terminal 2** (novo) e copia:

```bash
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
source venv/bin/activate
python3 -m src.console
```

**Resultado esperado:**
```
======================================================================
  Consola de Monitorização e Controlo (CMC)
  Sistema de Gestão de Tráfego Rodoviário (GSR)
======================================================================
  Digite 'help' para ver comandos disponíveis
======================================================================

gsr> 
```

---

## 3️⃣ TESTA COMANDOS

Agora escreve os comandos no **Terminal 2** (consola):

### Teste 1: Ver Ajuda
```
gsr> help
```

### Teste 2: Ver Mapa
```
gsr> map
```

### Teste 3: Ver Estatísticas
```
gsr> stats
```

### Teste 4: Monitorização ao Vivo
```
gsr> monitor
```
Pressiona `Ctrl+C` para parar

### Teste 5: Aumentar Tráfego
```
gsr> set roadRTG 1 50
```
Depois testa:
```
gsr> display
```
Vê Via 1 ficar mais cheia!

### Teste 6: Mudar Algoritmo
```
gsr> set algorithm 2
```
Os semáforos comportam-se diferente!

### Teste 7: Sair
```
gsr> exit
```

---

## ✅ SE ISTO FUNCIONAR, SISTEMA ESTÁ PRONTO! 🎉

**Ficheiros criados:**
- ✓ `src/console.py` - Consola criada
- ✓ `src/snmp_bridge.py` - Bridge para compartilhar MIB
- ✓ `src/central_system.py` - Atualizado com bridge

**Próximo passo:** Relatório final e entrega!
