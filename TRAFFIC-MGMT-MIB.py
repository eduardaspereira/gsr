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
# Produced by pysmi-1.6.3 at Fri Feb 20 22:24:21 2026
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

(ModuleCompliance,
 NotificationGroup) = mibBuilder.importSymbols(
    "SNMPv2-CONF",
    "ModuleCompliance",
    "NotificationGroup")

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
 TextualConvention) = mibBuilder.importSymbols(
    "SNMPv2-TC",
    "DisplayString",
    "PhysAddress",
    "TextualConvention")


# MODULE-IDENTITY

trafficMgmtMIB = ModuleIdentity(
    (1, 3, 6, 1, 3, 2026)
)
if mibBuilder.loadTexts:
    trafficMgmtMIB.setRevisions(
        ("2026-02-20 00:00",)
    )


# Types definitions


# TEXTUAL-CONVENTIONS



# MIB Managed Objects in the order of their OIDs

_TrafficObjects_ObjectIdentity = ObjectIdentity
trafficObjects = _TrafficObjects_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 1)
)
_TrafficGeneral_ObjectIdentity = ObjectIdentity
trafficGeneral = _TrafficGeneral_ObjectIdentity(
    (1, 3, 6, 1, 3, 2026, 1, 1)
)


class _SimStatus_Type(Integer32):
    """Custom type simStatus based on Integer32"""
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


_SimStatus_Type.__name__ = "Integer32"
_SimStatus_Object = MibScalar
simStatus = _SimStatus_Object(
    (1, 3, 6, 1, 3, 2026, 1, 1, 1),
    _SimStatus_Type()
)
simStatus.setMaxAccess("read-write")
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
if mibBuilder.loadTexts:
    algoYellowTime.setStatus("current")
if mibBuilder.loadTexts:
    algoYellowTime.setUnits("seconds")
_RoadTable_Object = MibTable
roadTable = _RoadTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2)
)
if mibBuilder.loadTexts:
    roadTable.setStatus("current")
_RoadEntry_Object = MibTableRow
roadEntry = _RoadEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1)
)
roadEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "roadIndex"),
)
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
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 1),
    _RoadIndex_Type()
)
roadIndex.setMaxAccess("not-accessible")
if mibBuilder.loadTexts:
    roadIndex.setStatus("current")
_RoadName_Type = DisplayString
_RoadName_Object = MibTableColumn
roadName = _RoadName_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 2),
    _RoadName_Type()
)
roadName.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadName.setStatus("current")


class _RoadType_Type(Integer32):
    """Custom type roadType based on Integer32"""
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


_RoadType_Type.__name__ = "Integer32"
_RoadType_Object = MibTableColumn
roadType = _RoadType_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 3),
    _RoadType_Type()
)
roadType.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadType.setStatus("current")
_RoadRTG_Type = Gauge32
_RoadRTG_Object = MibTableColumn
roadRTG = _RoadRTG_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 4),
    _RoadRTG_Type()
)
roadRTG.setMaxAccess("read-write")
if mibBuilder.loadTexts:
    roadRTG.setStatus("current")
_RoadMaxCapacity_Type = Gauge32
_RoadMaxCapacity_Object = MibTableColumn
roadMaxCapacity = _RoadMaxCapacity_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 5),
    _RoadMaxCapacity_Type()
)
roadMaxCapacity.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadMaxCapacity.setStatus("current")
_RoadVehicleCount_Type = Gauge32
_RoadVehicleCount_Object = MibTableColumn
roadVehicleCount = _RoadVehicleCount_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 6),
    _RoadVehicleCount_Type()
)
roadVehicleCount.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadVehicleCount.setStatus("current")


class _RoadLightColor_Type(Integer32):
    """Custom type roadLightColor based on Integer32"""
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


_RoadLightColor_Type.__name__ = "Integer32"
_RoadLightColor_Object = MibTableColumn
roadLightColor = _RoadLightColor_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 7),
    _RoadLightColor_Type()
)
roadLightColor.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadLightColor.setStatus("current")
_RoadTimeRemaining_Type = Integer32
_RoadTimeRemaining_Object = MibTableColumn
roadTimeRemaining = _RoadTimeRemaining_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 8),
    _RoadTimeRemaining_Type()
)
roadTimeRemaining.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadTimeRemaining.setStatus("current")
_RoadTotalCarsPassed_Type = Counter32
_RoadTotalCarsPassed_Object = MibTableColumn
roadTotalCarsPassed = _RoadTotalCarsPassed_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 9),
    _RoadTotalCarsPassed_Type()
)
roadTotalCarsPassed.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadTotalCarsPassed.setStatus("current")
_RoadAverageWaitTime_Type = Gauge32
_RoadAverageWaitTime_Object = MibTableColumn
roadAverageWaitTime = _RoadAverageWaitTime_Object(
    (1, 3, 6, 1, 3, 2026, 1, 2, 1, 10),
    _RoadAverageWaitTime_Type()
)
roadAverageWaitTime.setMaxAccess("read-only")
if mibBuilder.loadTexts:
    roadAverageWaitTime.setStatus("current")
if mibBuilder.loadTexts:
    roadAverageWaitTime.setUnits("seconds")
_RoadLinkTable_Object = MibTable
roadLinkTable = _RoadLinkTable_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3)
)
if mibBuilder.loadTexts:
    roadLinkTable.setStatus("current")
_RoadLinkEntry_Object = MibTableRow
roadLinkEntry = _RoadLinkEntry_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1)
)
roadLinkEntry.setIndexNames(
    (0, "TRAFFIC-MGMT-MIB", "roadIndex"),
    (0, "TRAFFIC-MGMT-MIB", "linkDestIndex"),
)
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
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 1),
    _LinkDestIndex_Type()
)
linkDestIndex.setMaxAccess("not-accessible")
if mibBuilder.loadTexts:
    linkDestIndex.setStatus("current")
_LinkFlowRate_Type = Gauge32
_LinkFlowRate_Object = MibTableColumn
linkFlowRate = _LinkFlowRate_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 2),
    _LinkFlowRate_Type()
)
linkFlowRate.setMaxAccess("read-write")
if mibBuilder.loadTexts:
    linkFlowRate.setStatus("current")


class _LinkActive_Type(Integer32):
    """Custom type linkActive based on Integer32"""
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


_LinkActive_Type.__name__ = "Integer32"
_LinkActive_Object = MibTableColumn
linkActive = _LinkActive_Object(
    (1, 3, 6, 1, 3, 2026, 1, 3, 1, 3),
    _LinkActive_Type()
)
linkActive.setMaxAccess("read-write")
if mibBuilder.loadTexts:
    linkActive.setStatus("current")

# Managed Objects groups


# Notification objects


# Notifications groups


# Agent capabilities


# Module compliance


# Export all MIB objects to the MIB builder

mibBuilder.exportSymbols(
    "TRAFFIC-MGMT-MIB",
    **{"trafficMgmtMIB": trafficMgmtMIB,
       "trafficObjects": trafficObjects,
       "trafficGeneral": trafficGeneral,
       "simStatus": simStatus,
       "simStepDuration": simStepDuration,
       "globalVehicleCount": globalVehicleCount,
       "algoMinGreenTime": algoMinGreenTime,
       "algoYellowTime": algoYellowTime,
       "roadTable": roadTable,
       "roadEntry": roadEntry,
       "roadIndex": roadIndex,
       "roadName": roadName,
       "roadType": roadType,
       "roadRTG": roadRTG,
       "roadMaxCapacity": roadMaxCapacity,
       "roadVehicleCount": roadVehicleCount,
       "roadLightColor": roadLightColor,
       "roadTimeRemaining": roadTimeRemaining,
       "roadTotalCarsPassed": roadTotalCarsPassed,
       "roadAverageWaitTime": roadAverageWaitTime,
       "roadLinkTable": roadLinkTable,
       "roadLinkEntry": roadLinkEntry,
       "linkDestIndex": linkDestIndex,
       "linkFlowRate": linkFlowRate,
       "linkActive": linkActive}
)
