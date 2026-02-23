# Árvore
<pre>
iso(1) . org(3) . dod(6) . internet(1) . private(4) . enterprises(1)  
 └── minhouniversity(9999)   
      └── trafficSystem(1)  
           └── trafficObjects(1)  
                └── roadTable(2)  
                     └── roadEntry(1) [INDEX { roadIndex }]  
                          ├── roadIndex(1)         INTEGER (ID da via)  
                          ├── roadName(2)          OCTET STRING (read-only)  
                          ├── roadRGT(4)           GAUGE32 (read-write)  
                          ├── roadMaxCap(5)        GAUGE32 (read-only)  
                          ├── roadVehicleCount(6)  GAUGE32 (read-only)  
                          ├── roadLightColor(7)    INTEGER { red(1), green(2), yellow(3) } (read-only)  
                          └── roadTimeRemaining(8) INTEGER (read-only)  
<pre>

**A Tabela (roadTable)**: Todos os dados relativos às vias rodoviárias e aos seus semáforos foram agregados conceptualmente nesta tabela. Cada linha (roadEntry) representa uma via física ou sumidouro.

**A Indexação**: O índice da tabela é o ID da via (ex: 1, 2, 3, 97). É este valor que é anexado ao final do OID (ex: .1.3.6.1.4.1.9999.1.1.2.1.6.1 para obter o número de veículos na via 1).

**Permissões**: Quase todos os objetos são de leitura (read-only) para monitorização pela CMC, sendo a exceção o roadRGT, que necessita de permissão de escrita (read-write) para que o administrador o possa manipular através da CMC.                        