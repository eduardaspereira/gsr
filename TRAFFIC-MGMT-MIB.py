# SNMP MIB module (TRAFFIC-MGMT-MIB) expressed in pysnmp data model.
#
# This Python module is designed to be imported and executed by the
# pysnmp library.
#
# See https://www.pysnmp.com/pysnmp for further information.
#
# Notes
# -----
# ASN.1 source file://./ProjetoGSR.mib
# Produced by pysmi-1.6.3 at Wed Mar 05 12:00:00 2026
# Using Python version 3.10.12
#
# Tabelas implementadas:
#   - crossroadTable (1.3.6.1.3.2026.1.2) - Cruzamentos
#   - roadTable       (1.3.6.1.3.2026.1.3) - Vias rodoviarias (objeto principal)
#   - trafficLightTable (1.3.6.1.3.2026.1.4) - Semaforos
#   - roadLinkTable   (1.3.6.1.3.2026.1.5) - Ligacoes entre vias

if 'mibBuilder' not in globals():
    import sys

    sys.stderr.write(__doc__)
    sys.exit(1)

# Import base ASN.1 objects

(Integer,
 OctetString,
 ObjectIdentifier) = mibBuilder.importSymbols(
    "ASN1",
    "Integer",
    "OctetString",
    "ObjectIdentifier")

(NamedValues,) = mibBuilder.importSymbols(
    "ASN1-ENUMERATION",
    "NamedValues")
(ConstraintsIntersection,
 ConstraintsUnion,
 SingleValueConstraint,
 ValueRangeConstraint,
 ValueSizeConstraint) = mibBuilder.importSymbols(
    "ASN1-REFINEMENT",
    "ConstraintsIntersection",
    "ConstraintsUnion",
    "SingleValueConstraint",
    "ValueRangeConstraint",
    "ValueSizeConstraint")

# Import SMI symbols

(ModuleCompliance,
 NotificationGroup,
 ObjectGroup) = mibBuilder.importSymbols(
    "SNMPv2-CONF",
    "ModuleCompliance",
    "NotificationGroup",
    "ObjectGroup")

(Bits,
 Counter32,
 Counter64,
 Gauge32,
 Integer32,
 IpAddress,
 ModuleIdentity,
 MibIdentifier,
 NotificationType,
 ObjectIdentity,
 MibScalar,
 MibTable,
 MibTableRow,
 MibTableColumn,
 TimeTicks,
 Unsigned32,
 experimental,
 iso) = mibBuilder.importSymbols(
    "SNMPv2-SMI",
    "Bits",
    "Counter32",
    "Counter64",
    "Gauge32",
    "Integer32",
    "IpAddress",
    "ModuleIdentity",
    "MibIdentifier",
    "NotificationType",
    "ObjectIdentity",
    "MibScalar",
    "MibTable",
    "MibTableRow",
    "MibTableColumn",
    "TimeTicks",
    "Unsigned32",
    "experimental",
    "iso")

(DisplayString,
 PhysAddress,
 RowStatus,
 TextualConvention) = mibBuilder.importSymbols(
    "SNMPv2-TC",
    "DisplayString",
    "PhysAddress",
    "RowStatus",
    "TextualConvention")


# MODULE-IDENTITY

trafficMgmtMIB = ModuleIdentity(
    (1, 3, 6, 1, 3, 2026)
)
trafficMgmtMIB.setOrganization("Universidade do Minho - Departamento de Informatica")
trafficMgmtMIB.setContactInfo("Mestrado em Engenharia Informatica - GSR 2025/2026")
trafficMgmtMIB.setDescription(
    "MIB experimental para o sistema de gestao de trafego "
    "rodoviario urbano. Define objetos para representar uma "
    "rede rodoviaria como um grafo dirigido."
)
if mibBuilder.loadTexts:
    trafficMgmtMIB.setRevisions(
        ("2026-02-20 00:00",)
    )


# Types definitions


class SimOperStatus(Integer32):
    """Estado operacional da simulacao."""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(*(1, 2, 3))
    )
    namedValues = NamedValues(
        *(("running", 1), ("stopped", 2), ("reset", 3))
    )


class RoadType(Integer32):
    """Tipo de via rodoviaria."""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(*(1, 2, 3))
    )
    namedValues = NamedValues(
        *(("normal", 1), ("sink", 2), ("source", 3))
    )


class TrafficColor(Integer32):
    """Cor atual do semaforo."""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(*(1, 2, 3))
    )
    namedValues = NamedValues(
        *(("red", 1), ("green", 2), ("yellow", 3))
    )


class TrafficAxis(Integer32):
    """Eixo direcional do semaforo no cruzamento."""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(*(1, 2))
    )
    namedValues = NamedValues(
        *(("ns", 1), ("ew", 2))
    )


class CrossroadMode(Integer32):
    """Modo de operacao do cruzamento."""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(*(1, 2, 3))
    )
    namedValues = NamedValues(
        *(("normal", 1), ("flashingYellow", 2), ("emergencyRed", 3))
    )


class LinkState(Integer32):
    """Estado operacional de uma ligacao entre vias."""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(*(1, 2))
    )
    namedValues = NamedValues(
        *(("active", 1), ("inactive", 2))
    )


# ======================================================================
# MIB Managed Objects in the order of their OIDs
# ======================================================================

# --- Hierarquia ---

_TrafficObjects_ObjectIdentity = ObjectIdentity
trafficObjects = _TrafficObjects_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 1)
)

_TrafficConformance_ObjectIdentity = ObjectIdentity
trafficConformance = _TrafficConformance_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 2)
)

_TrafficGeneral_ObjectIdentity = ObjectIdentity
trafficGeneral = _TrafficGeneral_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 1, 1)
)

# --- Escalares (trafficGeneral .1.1) ---

_SimStatus_Type = SimOperStatus
_SimStatus_Object = MibScalar
simStatus = _SimStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 1),
    _SimStatus_Type()
)
simStatus.setMaxAccess("read-write")
simStatus.setDescription("Estado operacional da simulacao.")
if mibBuilder.loadTexts:
    simStatus.setStatus("current")


class _SimStepDuration_Type(Integer32):
    """Custom type simStepDuration based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(1, 60),
    )


_SimStepDuration_Type.__name__ = "Integer32"
_SimStepDuration_Object = MibScalar
simStepDuration = _SimStepDuration_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 2),
    _SimStepDuration_Type()
)
simStepDuration.setMaxAccess("read-write")
simStepDuration.setDescription("Duracao de cada passo da simulacao.")
if mibBuilder.loadTexts:
    simStepDuration.setStatus("current")
if mibBuilder.loadTexts:
    simStepDuration.setUnits("seconds")

_GlobalVehicleCount_Type = Gauge32
_GlobalVehicleCount_Object = MibScalar
globalVehicleCount = _GlobalVehicleCount_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 3),
    _GlobalVehicleCount_Type()
)
globalVehicleCount.setMaxAccess("read-only")
globalVehicleCount.setDescription("Numero total de veiculos na rede.")
if mibBuilder.loadTexts:
    globalVehicleCount.setStatus("current")


class _AlgoMinGreenTime_Type(Integer32):
    """Custom type algoMinGreenTime based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(5, 120),
    )


_AlgoMinGreenTime_Type.__name__ = "Integer32"
_AlgoMinGreenTime_Object = MibScalar
algoMinGreenTime = _AlgoMinGreenTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 4),
    _AlgoMinGreenTime_Type()
)
algoMinGreenTime.setMaxAccess("read-write")
algoMinGreenTime.setDescription("Tempo minimo de verde para o algoritmo SD.")
if mibBuilder.loadTexts:
    algoMinGreenTime.setStatus("current")
if mibBuilder.loadTexts:
    algoMinGreenTime.setUnits("seconds")


class _AlgoYellowTime_Type(Integer32):
    """Custom type algoYellowTime based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(1, 10),
    )


_AlgoYellowTime_Type.__name__ = "Integer32"
_AlgoYellowTime_Object = MibScalar
algoYellowTime = _AlgoYellowTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 5),
    _AlgoYellowTime_Type()
)
algoYellowTime.setMaxAccess("read-only")
algoYellowTime.setDescription("Tempo fixo de amarelo para todos os semaforos.")
if mibBuilder.loadTexts:
    algoYellowTime.setStatus("current")
if mibBuilder.loadTexts:
    algoYellowTime.setUnits("seconds")

_TotalRoadCount_Type = Gauge32
_TotalRoadCount_Object = MibScalar
totalRoadCount = _TotalRoadCount_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 6),
    _TotalRoadCount_Type()
)
totalRoadCount.setMaxAccess("read-only")
totalRoadCount.setDescription("Numero total de vias na roadTable.")
if mibBuilder.loadTexts:
    totalRoadCount.setStatus("current")

_TotalCrossroadCount_Type = Gauge32
_TotalCrossroadCount_Object = MibScalar
totalCrossroadCount = _TotalCrossroadCount_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 7),
    _TotalCrossroadCount_Type()
)
totalCrossroadCount.setMaxAccess("read-only")
totalCrossroadCount.setDescription("Numero total de cruzamentos.")
if mibBuilder.loadTexts:
    totalCrossroadCount.setStatus("current")

# ======================================================================
# crossroadTable (.1.2)
# ======================================================================

_CrossroadTable_Object = MibTable
crossroadTable = _CrossroadTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2)
)
crossroadTable.setDescription("Tabela de cruzamentos da rede rodoviaria.")
if mibBuilder.loadTexts:
    crossroadTable.setStatus("current")

_CrossroadEntry_Object = MibTableRow
crossroadEntry = _CrossroadEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1)
)
crossroadEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "crossroadIndex"),
)
crossroadEntry.setDescription("Entrada para um cruzamento individual.")
if mibBuilder.loadTexts:
    crossroadEntry.setStatus("current")


class _CrossroadIndex_Type(Integer32):
    """Custom type crossroadIndex based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(1, 65535),
    )


_CrossroadIndex_Type.__name__ = "Integer32"
_CrossroadIndex_Object = MibTableColumn
crossroadIndex = _CrossroadIndex_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 1),
    _CrossroadIndex_Type()
)
crossroadIndex.setMaxAccess("not-accessible")
crossroadIndex.setDescription("Identificador unico do cruzamento.")
if mibBuilder.loadTexts:
    crossroadIndex.setStatus("current")

_CrossroadMode_Type = CrossroadMode
_CrossroadMode_Object = MibTableColumn
crossroadMode = _CrossroadMode_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 2),
    _CrossroadMode_Type()
)
crossroadMode.setMaxAccess("read-write")
crossroadMode.setDescription("Modo de operacao do cruzamento.")
if mibBuilder.loadTexts:
    crossroadMode.setStatus("current")

_CrossroadRowStatus_Type = RowStatus
_CrossroadRowStatus_Object = MibTableColumn
crossroadRowStatus = _CrossroadRowStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 3),
    _CrossroadRowStatus_Type()
)
crossroadRowStatus.setMaxAccess("read-create")
crossroadRowStatus.setDescription("RowStatus para crossroadTable.")
if mibBuilder.loadTexts:
    crossroadRowStatus.setStatus("current")

# ======================================================================
# roadTable (.1.3) - Objeto principal
# ======================================================================

_RoadTable_Object = MibTable
roadTable = _RoadTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3)
)
roadTable.setDescription("Tabela principal das vias rodoviarias.")
if mibBuilder.loadTexts:
    roadTable.setStatus("current")

_RoadEntry_Object = MibTableRow
roadEntry = _RoadEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1)
)
roadEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "roadIndex"),
)
roadEntry.setDescription("Entrada para uma via individual.")
if mibBuilder.loadTexts:
    roadEntry.setStatus("current")


class _RoadIndex_Type(Integer32):
    """Custom type roadIndex based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(1, 65535),
    )


_RoadIndex_Type.__name__ = "Integer32"
_RoadIndex_Object = MibTableColumn
roadIndex = _RoadIndex_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 1),
    _RoadIndex_Type()
)
roadIndex.setMaxAccess("not-accessible")
roadIndex.setDescription("Identificador unico da via rodoviaria.")
if mibBuilder.loadTexts:
    roadIndex.setStatus("current")

_RoadName_Type = DisplayString
_RoadName_Object = MibTableColumn
roadName = _RoadName_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 2),
    _RoadName_Type()
)
roadName.setMaxAccess("read-create")
roadName.setDescription("Nome descritivo da via rodoviaria.")
if mibBuilder.loadTexts:
    roadName.setStatus("current")

_RoadType_Type = RoadType
_RoadType_Object = MibTableColumn
roadType = _RoadType_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 3),
    _RoadType_Type()
)
roadType.setMaxAccess("read-create")
roadType.setDescription("Tipo da via: normal, sink ou source.")
if mibBuilder.loadTexts:
    roadType.setStatus("current")

_RoadRTG_Type = Gauge32
_RoadRTG_Object = MibTableColumn
roadRTG = _RoadRTG_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 4),
    _RoadRTG_Type()
)
roadRTG.setMaxAccess("read-write")
roadRTG.setDescription("Ritmo Gerador de Trafego (veiculos/min).")
if mibBuilder.loadTexts:
    roadRTG.setStatus("current")
if mibBuilder.loadTexts:
    roadRTG.setUnits("vehicles per minute")

_RoadMaxCapacity_Type = Gauge32
_RoadMaxCapacity_Object = MibTableColumn
roadMaxCapacity = _RoadMaxCapacity_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 5),
    _RoadMaxCapacity_Type()
)
roadMaxCapacity.setMaxAccess("read-create")
roadMaxCapacity.setDescription("Capacidade maxima da via em veiculos.")
if mibBuilder.loadTexts:
    roadMaxCapacity.setStatus("current")

_RoadVehicleCount_Type = Gauge32
_RoadVehicleCount_Object = MibTableColumn
roadVehicleCount = _RoadVehicleCount_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 6),
    _RoadVehicleCount_Type()
)
roadVehicleCount.setMaxAccess("read-only")
roadVehicleCount.setDescription("Numero atual de veiculos na via.")
if mibBuilder.loadTexts:
    roadVehicleCount.setStatus("current")

_RoadTotalCarsPassed_Type = Counter32
_RoadTotalCarsPassed_Object = MibTableColumn
roadTotalCarsPassed = _RoadTotalCarsPassed_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 7),
    _RoadTotalCarsPassed_Type()
)
roadTotalCarsPassed.setMaxAccess("read-only")
roadTotalCarsPassed.setDescription("Total acumulado de veiculos que atravessaram.")
if mibBuilder.loadTexts:
    roadTotalCarsPassed.setStatus("current")

_RoadAverageWaitTime_Type = Gauge32
_RoadAverageWaitTime_Object = MibTableColumn
roadAverageWaitTime = _RoadAverageWaitTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 8),
    _RoadAverageWaitTime_Type()
)
roadAverageWaitTime.setMaxAccess("read-only")
roadAverageWaitTime.setDescription("Tempo medio de espera em segundos.")
if mibBuilder.loadTexts:
    roadAverageWaitTime.setStatus("current")
if mibBuilder.loadTexts:
    roadAverageWaitTime.setUnits("seconds")

_RoadRowStatus_Type = RowStatus
_RoadRowStatus_Object = MibTableColumn
roadRowStatus = _RoadRowStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 9),
    _RoadRowStatus_Type()
)
roadRowStatus.setMaxAccess("read-create")
roadRowStatus.setDescription("RowStatus para roadTable.")
if mibBuilder.loadTexts:
    roadRowStatus.setStatus("current")

# ======================================================================
# trafficLightTable (.1.4) - Semaforos
# ======================================================================

_TrafficLightTable_Object = MibTable
trafficLightTable = _TrafficLightTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4)
)
trafficLightTable.setDescription("Tabela dos semaforos da rede rodoviaria.")
if mibBuilder.loadTexts:
    trafficLightTable.setStatus("current")

_TrafficLightEntry_Object = MibTableRow
trafficLightEntry = _TrafficLightEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1)
)
trafficLightEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "roadIndex"),
)
trafficLightEntry.setDescription("Entrada para um semaforo individual.")
if mibBuilder.loadTexts:
    trafficLightEntry.setStatus("current")

_TlCrossroadID_Type = Integer32
_TlCrossroadID_Object = MibTableColumn
tlCrossroadID = _TlCrossroadID_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 1),
    _TlCrossroadID_Type()
)
tlCrossroadID.setMaxAccess("read-create")
tlCrossroadID.setDescription("ID do cruzamento a que pertence o semaforo.")
if mibBuilder.loadTexts:
    tlCrossroadID.setStatus("current")

_TlAxis_Type = TrafficAxis
_TlAxis_Object = MibTableColumn
tlAxis = _TlAxis_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 2),
    _TlAxis_Type()
)
tlAxis.setMaxAccess("read-create")
tlAxis.setDescription("Eixo direcional do semaforo (NS ou EW).")
if mibBuilder.loadTexts:
    tlAxis.setStatus("current")

_TlColor_Type = TrafficColor
_TlColor_Object = MibTableColumn
tlColor = _TlColor_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 3),
    _TlColor_Type()
)
tlColor.setMaxAccess("read-only")
tlColor.setDescription("Cor atual do semaforo.")
if mibBuilder.loadTexts:
    tlColor.setStatus("current")

_TlTimeRemaining_Type = Integer32
_TlTimeRemaining_Object = MibTableColumn
tlTimeRemaining = _TlTimeRemaining_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 4),
    _TlTimeRemaining_Type()
)
tlTimeRemaining.setMaxAccess("read-only")
tlTimeRemaining.setDescription("Tempo restante ate a proxima mudanca de cor.")
if mibBuilder.loadTexts:
    tlTimeRemaining.setStatus("current")
if mibBuilder.loadTexts:
    tlTimeRemaining.setUnits("seconds")

_TlGreenDuration_Type = Integer32
_TlGreenDuration_Object = MibTableColumn
tlGreenDuration = _TlGreenDuration_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 5),
    _TlGreenDuration_Type()
)
tlGreenDuration.setMaxAccess("read-only")
tlGreenDuration.setDescription("Duracao do verde calculada pelo SD.")
if mibBuilder.loadTexts:
    tlGreenDuration.setStatus("current")
if mibBuilder.loadTexts:
    tlGreenDuration.setUnits("seconds")

_TlRedDuration_Type = Integer32
_TlRedDuration_Object = MibTableColumn
tlRedDuration = _TlRedDuration_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 6),
    _TlRedDuration_Type()
)
tlRedDuration.setMaxAccess("read-only")
tlRedDuration.setDescription("Duracao do vermelho calculada pelo SD.")
if mibBuilder.loadTexts:
    tlRedDuration.setStatus("current")
if mibBuilder.loadTexts:
    tlRedDuration.setUnits("seconds")

_TlRowStatus_Type = RowStatus
_TlRowStatus_Object = MibTableColumn
tlRowStatus = _TlRowStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 7),
    _TlRowStatus_Type()
)
tlRowStatus.setMaxAccess("read-create")
tlRowStatus.setDescription("RowStatus para trafficLightTable.")
if mibBuilder.loadTexts:
    tlRowStatus.setStatus("current")

# ======================================================================
# roadLinkTable (.1.5) - Ligacoes entre vias
# ======================================================================

_RoadLinkTable_Object = MibTable
roadLinkTable = _RoadLinkTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5)
)
roadLinkTable.setDescription("Tabela de ligacoes entre vias.")
if mibBuilder.loadTexts:
    roadLinkTable.setStatus("current")

_RoadLinkEntry_Object = MibTableRow
roadLinkEntry = _RoadLinkEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1)
)
roadLinkEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "roadIndex"),
    (0, "TRAFFIC-MGMT-MIB", "linkDestIndex"),
)
roadLinkEntry.setDescription("Ligacao entre via de origem e via de destino.")
if mibBuilder.loadTexts:
    roadLinkEntry.setStatus("current")


class _LinkDestIndex_Type(Integer32):
    """Custom type linkDestIndex based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(1, 65535),
    )


_LinkDestIndex_Type.__name__ = "Integer32"
_LinkDestIndex_Object = MibTableColumn
linkDestIndex = _LinkDestIndex_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 1),
    _LinkDestIndex_Type()
)
linkDestIndex.setMaxAccess("not-accessible")
linkDestIndex.setDescription("ID da via de destino.")
if mibBuilder.loadTexts:
    linkDestIndex.setStatus("current")

_LinkFlowRate_Type = Gauge32
_LinkFlowRate_Object = MibTableColumn
linkFlowRate = _LinkFlowRate_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 2),
    _LinkFlowRate_Type()
)
linkFlowRate.setMaxAccess("read-create")
linkFlowRate.setDescription("Ritmo de distribuicao (veiculos/min).")
if mibBuilder.loadTexts:
    linkFlowRate.setStatus("current")
if mibBuilder.loadTexts:
    linkFlowRate.setUnits("vehicles per minute")

_LinkActive_Type = LinkState
_LinkActive_Object = MibTableColumn
linkActive = _LinkActive_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 3),
    _LinkActive_Type()
)
linkActive.setMaxAccess("read-create")
linkActive.setDescription("Estado da ligacao: active ou inactive.")
if mibBuilder.loadTexts:
    linkActive.setStatus("current")

_LinkCarsPassed_Type = Counter32
_LinkCarsPassed_Object = MibTableColumn
linkCarsPassed = _LinkCarsPassed_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 4),
    _LinkCarsPassed_Type()
)
linkCarsPassed.setMaxAccess("read-only")
linkCarsPassed.setDescription("Total de veiculos que passaram nesta ligacao.")
if mibBuilder.loadTexts:
    linkCarsPassed.setStatus("current")

_LinkRowStatus_Type = RowStatus
_LinkRowStatus_Object = MibTableColumn
linkRowStatus = _LinkRowStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 5),
    _LinkRowStatus_Type()
)
linkRowStatus.setMaxAccess("read-create")
linkRowStatus.setDescription("RowStatus para roadLinkTable.")
if mibBuilder.loadTexts:
    linkRowStatus.setStatus("current")

# ======================================================================
# Conformidade
# ======================================================================

_TrafficMIBCompliances_ObjectIdentity = ObjectIdentity
trafficMIBCompliances = _TrafficMIBCompliances_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 2, 1)
)

_TrafficMIBGroups_ObjectIdentity = ObjectIdentity
trafficMIBGroups = _TrafficMIBGroups_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 2, 2)
)

trafficGeneralGroup = ObjectGroup(
    (1, 3, 6, 1, 3, 2026, 2, 2, 1)
).setObjects(
    ("TRAFFIC-MGMT-MIB", "simStatus"),
    ("TRAFFIC-MGMT-MIB", "simStepDuration"),
    ("TRAFFIC-MGMT-MIB", "globalVehicleCount"),
    ("TRAFFIC-MGMT-MIB", "algoMinGreenTime"),
    ("TRAFFIC-MGMT-MIB", "algoYellowTime"),
    ("TRAFFIC-MGMT-MIB", "totalRoadCount"),
    ("TRAFFIC-MGMT-MIB", "totalCrossroadCount"),
)
trafficGeneralGroup.setDescription("Grupo de objetos escalares gerais.")
if mibBuilder.loadTexts:
    trafficGeneralGroup.setStatus("current")

crossroadGroup = ObjectGroup(
    (1, 3, 6, 1, 3, 2026, 2, 2, 2)
).setObjects(
    ("TRAFFIC-MGMT-MIB", "crossroadMode"),
    ("TRAFFIC-MGMT-MIB", "crossroadRowStatus"),
)
crossroadGroup.setDescription("Grupo de objetos para cruzamentos.")
if mibBuilder.loadTexts:
    crossroadGroup.setStatus("current")

roadGroup = ObjectGroup(
    (1, 3, 6, 1, 3, 2026, 2, 2, 3)
).setObjects(
    ("TRAFFIC-MGMT-MIB", "roadName"),
    ("TRAFFIC-MGMT-MIB", "roadType"),
    ("TRAFFIC-MGMT-MIB", "roadRTG"),
    ("TRAFFIC-MGMT-MIB", "roadMaxCapacity"),
    ("TRAFFIC-MGMT-MIB", "roadVehicleCount"),
    ("TRAFFIC-MGMT-MIB", "roadTotalCarsPassed"),
    ("TRAFFIC-MGMT-MIB", "roadAverageWaitTime"),
    ("TRAFFIC-MGMT-MIB", "roadRowStatus"),
)
roadGroup.setDescription("Grupo de objetos para vias rodoviarias.")
if mibBuilder.loadTexts:
    roadGroup.setStatus("current")

trafficLightGroup = ObjectGroup(
    (1, 3, 6, 1, 3, 2026, 2, 2, 4)
).setObjects(
    ("TRAFFIC-MGMT-MIB", "tlCrossroadID"),
    ("TRAFFIC-MGMT-MIB", "tlAxis"),
    ("TRAFFIC-MGMT-MIB", "tlColor"),
    ("TRAFFIC-MGMT-MIB", "tlTimeRemaining"),
    ("TRAFFIC-MGMT-MIB", "tlGreenDuration"),
    ("TRAFFIC-MGMT-MIB", "tlRedDuration"),
    ("TRAFFIC-MGMT-MIB", "tlRowStatus"),
)
trafficLightGroup.setDescription("Grupo de objetos para semaforos.")
if mibBuilder.loadTexts:
    trafficLightGroup.setStatus("current")

roadLinkGroup = ObjectGroup(
    (1, 3, 6, 1, 3, 2026, 2, 2, 5)
).setObjects(
    ("TRAFFIC-MGMT-MIB", "linkFlowRate"),
    ("TRAFFIC-MGMT-MIB", "linkActive"),
    ("TRAFFIC-MGMT-MIB", "linkCarsPassed"),
    ("TRAFFIC-MGMT-MIB", "linkRowStatus"),
)
roadLinkGroup.setDescription("Grupo de objetos para ligacoes entre vias.")
if mibBuilder.loadTexts:
    roadLinkGroup.setStatus("current")

trafficMIBCompliance = ModuleCompliance(
    (1, 3, 6, 1, 3, 2026, 2, 1, 1)
)
trafficMIBCompliance.setDescription("Conformidade da TRAFFIC-MGMT-MIB.")
if mibBuilder.loadTexts:
    trafficMIBCompliance.setStatus("current")

# ======================================================================
# Export all MIB objects to the MIB builder
# ======================================================================

mibBuilder.exportSymbols(
    "TRAFFIC-MGMT-MIB",
    **{"SimOperStatus": SimOperStatus,
       "RoadType": RoadType,
       "TrafficColor": TrafficColor,
       "TrafficAxis": TrafficAxis,
       "CrossroadMode": CrossroadMode,
       "LinkState": LinkState,
       "trafficMgmtMIB": trafficMgmtMIB,
       "trafficObjects": trafficObjects,
       "trafficConformance": trafficConformance,
       "trafficGeneral": trafficGeneral,
       "simStatus": simStatus,
       "simStepDuration": simStepDuration,
       "globalVehicleCount": globalVehicleCount,
       "algoMinGreenTime": algoMinGreenTime,
       "algoYellowTime": algoYellowTime,
       "totalRoadCount": totalRoadCount,
       "totalCrossroadCount": totalCrossroadCount,
       "crossroadTable": crossroadTable,
       "crossroadEntry": crossroadEntry,
       "crossroadIndex": crossroadIndex,
       "crossroadMode": crossroadMode,
       "crossroadRowStatus": crossroadRowStatus,
       "roadTable": roadTable,
       "roadEntry": roadEntry,
       "roadIndex": roadIndex,
       "roadName": roadName,
       "roadType": roadType,
       "roadRTG": roadRTG,
       "roadMaxCapacity": roadMaxCapacity,
       "roadVehicleCount": roadVehicleCount,
       "roadTotalCarsPassed": roadTotalCarsPassed,
       "roadAverageWaitTime": roadAverageWaitTime,
       "roadRowStatus": roadRowStatus,
       "trafficLightTable": trafficLightTable,
       "trafficLightEntry": trafficLightEntry,
       "tlCrossroadID": tlCrossroadID,
       "tlAxis": tlAxis,
       "tlColor": tlColor,
       "tlTimeRemaining": tlTimeRemaining,
       "tlGreenDuration": tlGreenDuration,
       "tlRedDuration": tlRedDuration,
       "tlRowStatus": tlRowStatus,
       "roadLinkTable": roadLinkTable,
       "roadLinkEntry": roadLinkEntry,
       "linkDestIndex": linkDestIndex,
       "linkFlowRate": linkFlowRate,
       "linkActive": linkActive,
       "linkCarsPassed": linkCarsPassed,
       "linkRowStatus": linkRowStatus,
       "trafficMIBCompliances": trafficMIBCompliances,
       "trafficMIBGroups": trafficMIBGroups,
       "trafficGeneralGroup": trafficGeneralGroup,
       "crossroadGroup": crossroadGroup,
       "roadGroup": roadGroup,
       "trafficLightGroup": trafficLightGroup,
       "roadLinkGroup": roadLinkGroup,
       "trafficMIBCompliance": trafficMIBCompliance}
)
