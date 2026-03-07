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
# Produced by pysmi-1.6.3 at Thu Mar 06 12:00:00 2026
# On host DESKTOP-P3U48S2 platform Linux version 6.6.87.2-microsoft-standard-WSL2 by user duds
# Using Python version 3.10.12 (main, Jan 26 2026, 14:55:28) [GCC 11.4.0]

if 'mibBuilder' not in globals():
    import sys

    sys.stderr.write(__doc__)
    sys.exit(1)

# Import base ASN.1 objects even if this MIB does not use it

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

# Import SMI symbols from the MIBs this MIB depends on



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
if mibBuilder.loadTexts:
    trafficMgmtMIB.setRevisions(
        ("2026-03-06 00:00",)
    )
if mibBuilder.loadTexts:
    trafficMgmtMIB.setDescription(
        "MIB experimental para gestão de tráfego rodoviário urbano."
    )


# Types definitions


class SimOperStatus(Integer32):
    """Custom type SimOperStatus based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(
            *(1,
              2,
              3)
        )
    )
    namedValues = NamedValues(
        *(("running", 1),
          ("stopped", 2),
          ("reset", 3))
    )


class RoadType(Integer32):
    """Custom type RoadType based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(
            *(1,
              2,
              3)
        )
    )
    namedValues = NamedValues(
        *(("normal", 1),
          ("sink", 2),
          ("source", 3))
    )


class TrafficColor(Integer32):
    """Custom type TrafficColor based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(
            *(1,
              2,
              3)
        )
    )
    namedValues = NamedValues(
        *(("red", 1),
          ("green", 2),
          ("yellow", 3))
    )


class TrafficAxis(Integer32):
    """Custom type TrafficAxis based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(
            *(1,
              2)
        )
    )
    namedValues = NamedValues(
        *(("ns", 1),
          ("ew", 2))
    )


class CrossroadMode(Integer32):
    """Custom type CrossroadMode based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(
            *(1,
              2,
              3)
        )
    )
    namedValues = NamedValues(
        *(("normal", 1),
          ("flashingYellow", 2),
          ("allRed", 3))
    )


class LinkState(Integer32):
    """Custom type LinkState based on Integer32"""
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        SingleValueConstraint(
            *(1,
              2)
        )
    )
    namedValues = NamedValues(
        *(("active", 1),
          ("inactive", 2))
    )


# TEXTUAL-CONVENTIONS


# MIB Managed Objects in the order of their OIDs

# --- trafficObjects ---

_TrafficObjects_ObjectIdentity = ObjectIdentity
trafficObjects = _TrafficObjects_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 1)
)

# --- trafficGeneral ---

_TrafficGeneral_ObjectIdentity = ObjectIdentity
trafficGeneral = _TrafficGeneral_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 1, 1)
)

# simStatus (1)
_SimStatus_Type = SimOperStatus
_SimStatus_Object = MibScalar
simStatus = _SimStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 1),
    _SimStatus_Type()
)
simStatus.setMaxAccess("read-write")
if mibBuilder.loadTexts:
    simStatus.setStatus("current")

# simStepDuration (2)
class _SimStepDuration_Type(Integer32):
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
if mibBuilder.loadTexts:
    simStepDuration.setStatus("current")
if mibBuilder.loadTexts:
    simStepDuration.setUnits("seconds")

# simElapsedTime (3)
_SimElapsedTime_Type = Counter32
_SimElapsedTime_Object = MibScalar
simElapsedTime = _SimElapsedTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 3),
    _SimElapsedTime_Type()
)
simElapsedTime.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    simElapsedTime.setStatus("current")
if mibBuilder.loadTexts:
    simElapsedTime.setUnits("seconds")

# globalVehicleCount (4)
_GlobalVehicleCount_Type = Gauge32
_GlobalVehicleCount_Object = MibScalar
globalVehicleCount = _GlobalVehicleCount_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 4),
    _GlobalVehicleCount_Type()
)
globalVehicleCount.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    globalVehicleCount.setStatus("current")

# globalAvgWaitTime (5)
_GlobalAvgWaitTime_Type = Gauge32
_GlobalAvgWaitTime_Object = MibScalar
globalAvgWaitTime = _GlobalAvgWaitTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 5),
    _GlobalAvgWaitTime_Type()
)
globalAvgWaitTime.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    globalAvgWaitTime.setStatus("current")
if mibBuilder.loadTexts:
    globalAvgWaitTime.setUnits("seconds")

# totalVehiclesEntered (6)
_TotalVehiclesEntered_Type = Counter32
_TotalVehiclesEntered_Object = MibScalar
totalVehiclesEntered = _TotalVehiclesEntered_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 6),
    _TotalVehiclesEntered_Type()
)
totalVehiclesEntered.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    totalVehiclesEntered.setStatus("current")

# totalVehiclesExited (7)
_TotalVehiclesExited_Type = Counter32
_TotalVehiclesExited_Object = MibScalar
totalVehiclesExited = _TotalVehiclesExited_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 7),
    _TotalVehiclesExited_Type()
)
totalVehiclesExited.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    totalVehiclesExited.setStatus("current")

# algoMinGreenTime (8)
class _AlgoMinGreenTime_Type(Integer32):
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(5, 120),
    )

_AlgoMinGreenTime_Type.__name__ = "Integer32"
_AlgoMinGreenTime_Object = MibScalar
algoMinGreenTime = _AlgoMinGreenTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 8),
    _AlgoMinGreenTime_Type()
)
algoMinGreenTime.setMaxAccess("read-write")
if mibBuilder.loadTexts:
    algoMinGreenTime.setStatus("current")
if mibBuilder.loadTexts:
    algoMinGreenTime.setUnits("seconds")

# algoMaxGreenTime (9)
class _AlgoMaxGreenTime_Type(Integer32):
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(10, 300),
    )

_AlgoMaxGreenTime_Type.__name__ = "Integer32"
_AlgoMaxGreenTime_Object = MibScalar
algoMaxGreenTime = _AlgoMaxGreenTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 9),
    _AlgoMaxGreenTime_Type()
)
algoMaxGreenTime.setMaxAccess("read-write")
if mibBuilder.loadTexts:
    algoMaxGreenTime.setStatus("current")
if mibBuilder.loadTexts:
    algoMaxGreenTime.setUnits("seconds")

# algoYellowTime (10)
class _AlgoYellowTime_Type(Integer32):
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(1, 10),
    )

_AlgoYellowTime_Type.__name__ = "Integer32"
_AlgoYellowTime_Object = MibScalar
algoYellowTime = _AlgoYellowTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 10),
    _AlgoYellowTime_Type()
)
algoYellowTime.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    algoYellowTime.setStatus("current")
if mibBuilder.loadTexts:
    algoYellowTime.setUnits("seconds")


# --- crossroadTable (2) ---

_CrossroadTable_Object = MibTable
crossroadTable = _CrossroadTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2)
)
if mibBuilder.loadTexts:
    crossroadTable.setStatus("current")

_CrossroadEntry_Object = MibTableRow
crossroadEntry = _CrossroadEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1)
)
crossroadEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "crossroadIndex"),
)
if mibBuilder.loadTexts:
    crossroadEntry.setStatus("current")

class _CrossroadIndex_Type(Integer32):
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
if mibBuilder.loadTexts:
    crossroadIndex.setStatus("current")

_CrossroadMode_Type = CrossroadMode
_CrossroadMode_Object = MibTableColumn
crossroadMode = _CrossroadMode_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 2),
    _CrossroadMode_Type()
)
crossroadMode.setMaxAccess("read-write")
if mibBuilder.loadTexts:
    crossroadMode.setStatus("current")

_CrossroadRowStatus_Type = RowStatus
_CrossroadRowStatus_Object = MibTableColumn
crossroadRowStatus = _CrossroadRowStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 3),
    _CrossroadRowStatus_Type()
)
crossroadRowStatus.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    crossroadRowStatus.setStatus("current")


# --- roadTable (3) ---

_RoadTable_Object = MibTable
roadTable = _RoadTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3)
)
if mibBuilder.loadTexts:
    roadTable.setStatus("current")

_RoadEntry_Object = MibTableRow
roadEntry = _RoadEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1)
)
roadEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "roadIndex"),
)
if mibBuilder.loadTexts:
    roadEntry.setStatus("current")

class _RoadIndex_Type(Integer32):
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
if mibBuilder.loadTexts:
    roadIndex.setStatus("current")

_RoadName_Type = DisplayString
_RoadName_Object = MibTableColumn
roadName = _RoadName_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 2),
    _RoadName_Type()
)
roadName.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    roadName.setStatus("current")

_RoadType_Type = RoadType
_RoadType_Object = MibTableColumn
roadType = _RoadType_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 3),
    _RoadType_Type()
)
roadType.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    roadType.setStatus("current")

_RoadRTG_Type = Gauge32
_RoadRTG_Object = MibTableColumn
roadRTG = _RoadRTG_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 4),
    _RoadRTG_Type()
)
roadRTG.setMaxAccess("read-write")
if mibBuilder.loadTexts:
    roadRTG.setStatus("current")

_RoadMaxCapacity_Type = Gauge32
_RoadMaxCapacity_Object = MibTableColumn
roadMaxCapacity = _RoadMaxCapacity_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 5),
    _RoadMaxCapacity_Type()
)
roadMaxCapacity.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    roadMaxCapacity.setStatus("current")

_RoadVehicleCount_Type = Gauge32
_RoadVehicleCount_Object = MibTableColumn
roadVehicleCount = _RoadVehicleCount_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 6),
    _RoadVehicleCount_Type()
)
roadVehicleCount.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadVehicleCount.setStatus("current")

_RoadTotalCarsPassed_Type = Counter32
_RoadTotalCarsPassed_Object = MibTableColumn
roadTotalCarsPassed = _RoadTotalCarsPassed_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 7),
    _RoadTotalCarsPassed_Type()
)
roadTotalCarsPassed.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadTotalCarsPassed.setStatus("current")

_RoadAverageWaitTime_Type = Gauge32
_RoadAverageWaitTime_Object = MibTableColumn
roadAverageWaitTime = _RoadAverageWaitTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 8),
    _RoadAverageWaitTime_Type()
)
roadAverageWaitTime.setMaxAccess("read-only")
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
if mibBuilder.loadTexts:
    roadRowStatus.setStatus("current")


# --- trafficLightTable (4) ---

_TrafficLightTable_Object = MibTable
trafficLightTable = _TrafficLightTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4)
)
if mibBuilder.loadTexts:
    trafficLightTable.setStatus("current")

_TrafficLightEntry_Object = MibTableRow
trafficLightEntry = _TrafficLightEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1)
)
trafficLightEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "roadIndex"),
)
if mibBuilder.loadTexts:
    trafficLightEntry.setStatus("current")

_TlCrossroadID_Type = Integer32
_TlCrossroadID_Object = MibTableColumn
tlCrossroadID = _TlCrossroadID_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 1),
    _TlCrossroadID_Type()
)
tlCrossroadID.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    tlCrossroadID.setStatus("current")

_TlAxis_Type = TrafficAxis
_TlAxis_Object = MibTableColumn
tlAxis = _TlAxis_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 2),
    _TlAxis_Type()
)
tlAxis.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    tlAxis.setStatus("current")

_TlColor_Type = TrafficColor
_TlColor_Object = MibTableColumn
tlColor = _TlColor_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 3),
    _TlColor_Type()
)
tlColor.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    tlColor.setStatus("current")

_TlTimeRemaining_Type = Integer32
_TlTimeRemaining_Object = MibTableColumn
tlTimeRemaining = _TlTimeRemaining_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 4),
    _TlTimeRemaining_Type()
)
tlTimeRemaining.setMaxAccess("read-only")
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
if mibBuilder.loadTexts:
    tlRedDuration.setStatus("current")
if mibBuilder.loadTexts:
    tlRedDuration.setUnits("seconds")

_TlDrainRate_Type = Gauge32
_TlDrainRate_Object = MibTableColumn
tlDrainRate = _TlDrainRate_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 7),
    _TlDrainRate_Type()
)
tlDrainRate.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    tlDrainRate.setStatus("current")

_TlRowStatus_Type = RowStatus
_TlRowStatus_Object = MibTableColumn
tlRowStatus = _TlRowStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 4, 1, 8),
    _TlRowStatus_Type()
)
tlRowStatus.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    tlRowStatus.setStatus("current")


# --- roadLinkTable (5) ---

_RoadLinkTable_Object = MibTable
roadLinkTable = _RoadLinkTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5)
)
if mibBuilder.loadTexts:
    roadLinkTable.setStatus("current")

_RoadLinkEntry_Object = MibTableRow
roadLinkEntry = _RoadLinkEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1)
)
roadLinkEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "linkIndex"),
)
if mibBuilder.loadTexts:
    roadLinkEntry.setStatus("current")

class _LinkIndex_Type(Integer32):
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(1, 65535),
    )

_LinkIndex_Type.__name__ = "Integer32"
_LinkIndex_Object = MibTableColumn
linkIndex = _LinkIndex_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 1),
    _LinkIndex_Type()
)
linkIndex.setMaxAccess("not-accessible")
if mibBuilder.loadTexts:
    linkIndex.setStatus("current")

_LinkSourceIndex_Type = Integer32
_LinkSourceIndex_Object = MibTableColumn
linkSourceIndex = _LinkSourceIndex_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 2),
    _LinkSourceIndex_Type()
)
linkSourceIndex.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    linkSourceIndex.setStatus("current")

class _LinkDestIndex_Type(Integer32):
    subtypeSpec = Integer32.subtypeSpec
    subtypeSpec += ConstraintsUnion(
        ValueRangeConstraint(1, 65535),
    )

_LinkDestIndex_Type.__name__ = "Integer32"
_LinkDestIndex_Object = MibTableColumn
linkDestIndex = _LinkDestIndex_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 3),
    _LinkDestIndex_Type()
)
linkDestIndex.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    linkDestIndex.setStatus("current")

_LinkFlowRate_Type = Gauge32
_LinkFlowRate_Object = MibTableColumn
linkFlowRate = _LinkFlowRate_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 4),
    _LinkFlowRate_Type()
)
linkFlowRate.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    linkFlowRate.setStatus("current")

_LinkActive_Type = LinkState
_LinkActive_Object = MibTableColumn
linkActive = _LinkActive_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 5),
    _LinkActive_Type()
)
linkActive.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    linkActive.setStatus("current")

_LinkCarsPassed_Type = Counter32
_LinkCarsPassed_Object = MibTableColumn
linkCarsPassed = _LinkCarsPassed_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 6),
    _LinkCarsPassed_Type()
)
linkCarsPassed.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    linkCarsPassed.setStatus("current")

_LinkRowStatus_Type = RowStatus
_LinkRowStatus_Object = MibTableColumn
linkRowStatus = _LinkRowStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 5, 1, 7),
    _LinkRowStatus_Type()
)
linkRowStatus.setMaxAccess("read-create")
if mibBuilder.loadTexts:
    linkRowStatus.setStatus("current")




# Export all MIB objects to the MIB builder

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
       "trafficGeneral": trafficGeneral,
       "simStatus": simStatus,
       "simStepDuration": simStepDuration,
       "simElapsedTime": simElapsedTime,
       "globalVehicleCount": globalVehicleCount,
       "globalAvgWaitTime": globalAvgWaitTime,
       "totalVehiclesEntered": totalVehiclesEntered,
       "totalVehiclesExited": totalVehiclesExited,
       "algoMinGreenTime": algoMinGreenTime,
       "algoMaxGreenTime": algoMaxGreenTime,
       "algoYellowTime": algoYellowTime,
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
       "tlDrainRate": tlDrainRate,
       "tlRowStatus": tlRowStatus,
       "roadLinkTable": roadLinkTable,
       "roadLinkEntry": roadLinkEntry,
       "linkIndex": linkIndex,
       "linkSourceIndex": linkSourceIndex,
       "linkDestIndex": linkDestIndex,
       "linkFlowRate": linkFlowRate,
       "linkActive": linkActive,
       "linkCarsPassed": linkCarsPassed,
       "linkRowStatus": linkRowStatus}
)
