
## Compilar MIB para .py
```bash
mibdump --mib-source=file:///usr/share/snmp/mibs --mib-source=https://mibs.pysnmp.com/asn1/@mib@ --mib-source=file://. --destination-directory=. --destination-format=pysnmp ProjetoGSR.mib
```

## Comando para testar
```bash
snmpwalk -v2c -c public 127.0.0.1:1161 1.3.6.1.4.1.9999
```

## Significado do output
# Ritmo Gerador de Tráfego
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

# Contagem veículos em cada via
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

# Cor dos Semáforos
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