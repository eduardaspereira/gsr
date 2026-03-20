# 🚀 COMO TESTAR - RESUMO RÁPIDO

## 1️⃣ Teste Rápido (30 segundos) - ✅ PRIMEIRO FAZER ISTO

```bash
cd /Users/gugafm11/Desktop/Mestrado-2semestre/gsr
source venv/bin/activate
python3 quick_test.py
```

**Resultado esperado:**
```
✓ Teste concluído com sucesso!
```

---

## 2️⃣ Teste Completo (2 Terminais)

### Terminal 1: Sistema Central
```bash
python3 -m src.central_system -H 127.0.0.1 -p 10161
```
✓ Deixa a rodar

### Terminal 2: Consola
```bash
python3 -m src.console
```

**Comandos:**
```
gsr> map              # Ver topologia
gsr> stats            # Ver estatísticas
gsr> monitor          # Atualizar continuamente (Ctrl+C para parar)
gsr> set roadRTG 1 50 # Aumentar tráfego
gsr> set algorithm 2  # Mudar algoritmo
gsr> exit             # Sair
```

---

## 3️⃣ Teste Gráfico

```bash
python3 cmc_grafica.py
```

Dashboard ASCII dinâmico que atualiza a cada 5 segundos.

---

## ✅ Se Tudo Isto Funcionar = SISTEMA PRONTO! 🎉

Vê o ficheiro completo: `GUIA_TESTES_COMPLETO.md`
