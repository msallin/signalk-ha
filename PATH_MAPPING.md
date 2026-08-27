# PATH Mapping

This document captures current Signal K -> Home Assistant naming and unit mapping behavior for `signalk_ha`.

## Marine Convention References

- Signal K specification (path semantics and true/magnetic meanings): https://signalk.org/specification
- Public NMEA sentence reference (legacy and common abbreviations such as HDT/HDM/DBT/DBS/DBK): https://gpsd.gitlab.io/gpsd/NMEA.html

## Exact Path Mapping

| path | display name | unit | conversion |
|---|---|---|---|
| `environment.depth.belowKeel` | `DBK` | `m` | `` |
| `environment.depth.belowSurface` | `DBS` | `m` | `` |
| `environment.depth.belowTransducer` | `DBT` | `m` | `` |
| `environment.wind.angleApparent` | `AWA` | `°` | `rad_to_deg` |
| `environment.wind.angleTrueGround` | `TWA Ground` | `°` | `rad_to_deg` |
| `environment.wind.angleTrueWater` | `TWA` | `°` | `rad_to_deg` |
| `environment.wind.directionMagnetic` | `GWD Magnetic` | `° M` | `rad_to_deg` |
| `environment.wind.directionTrue` | `GWD` | `° T` | `rad_to_deg` |
| `environment.wind.speedApparent` | `AWS` | `kn` | `ms_to_knots` |
| `environment.wind.speedOverGround` | `GWS` | `kn` | `ms_to_knots` |
| `environment.wind.speedTrue` | `TWS` | `kn` | `ms_to_knots` |
| `navigation.courseOverGroundMagnetic` | `COG Magnetic` | `° M` | `rad_to_deg` |
| `navigation.courseOverGroundTrue` | `COG` | `° T` | `rad_to_deg` |
| `navigation.headingMagnetic` | `HDM` | `° M` | `rad_to_deg` |
| `navigation.headingTrue` | `HDT` | `° T` | `rad_to_deg` |
| `navigation.speedOverGround` | `SOG` | `kn` | `ms_to_knots` |
| `navigation.speedThroughWater` | `STW` | `kn` | `ms_to_knots` |
| `tanks.freshWater.0.currentLevel` | `` | `%` | `ratio_to_percent` |

## State Class for Unmapped Paths

Paths with no entry in the exact or pattern mapping get their `state_class` from their
unit. `MEASUREMENT` is applied when the unit is one of `A`, `Hz`, `K`, `Pa`, `V`, `W`,
matched case-insensitively, and never for a path containing `setpoint`, `warn`, `fault`,
`limit` or `nominal`, which are configuration rather than measurements.

The allowlist is narrower than the schema vocabulary on purpose. Units the integration
may still convert (`m`, `s`, `m/s`, `m3`, `ratio`, `%`) are left out, because changing
the unit of a sensor that already has statistics costs the user a `units_changed`
repair.
`J` and `C` are left out because they carry running totals, and `rad` because the
arithmetic mean of a bearing is meaningless.

An explicit mapping always wins, and a `state_class` already stored in the entity
registry is never replaced.

## Primrose Snapshot (as discovered in HA)

Generated from `http://primrose.local:3000/signalk/v1/api/vessels/self` using current discovery logic.

Generated at: 2026-03-19 11:17:01Z

| path | name | unit |
|---|---|---|
| `design.airHeight` | `Air Height` | `m` |
| `design.beam` | `Beam` | `m` |
| `design.bowAnchorRollerHeight` | `Bow Anchor Roller Height` | `m` |
| `electrical.displays.navico.default.brightness` | `Default Brightness` | `ratio` |
| `electrical.displays.navico.group1.brightness` | `Group1 Group 1 Brightness` | `ratio` |
| `electrical.displays.navico.group2.brightness` | `Group2 Group 2 Brightness` | `ratio` |
| `electrical.displays.navico.group3.brightness` | `Group3 Group 3 Brightness` | `ratio` |
| `electrical.displays.navico.group4.brightness` | `Group4 Group 4 Brightness` | `ratio` |
| `electrical.displays.navico.group5.brightness` | `Group5 Group 5 Brightness` | `ratio` |
| `electrical.displays.navico.group6.brightness` | `Group 6 Brightness` | `ratio` |
| `electrical.displays.raymarine.cockpit.brightness` | `Cockpit Brightness` | `ratio` |
| `electrical.displays.raymarine.cockpit.color` | `Cockpit Color` | `` |
| `electrical.displays.raymarine.flybridge.brightness` | `Flybridge Brightness` | `ratio` |
| `electrical.displays.raymarine.flybridge.color` | `Flybridge Color` | `` |
| `electrical.displays.raymarine.group1.brightness` | `Group1 Group 1 Brightness` | `ratio` |
| `electrical.displays.raymarine.group1.color` | `Group 1 Color` | `` |
| `electrical.displays.raymarine.group2.brightness` | `Group2 Group 2 Brightness` | `ratio` |
| `electrical.displays.raymarine.group2.color` | `Group 2 Color` | `` |
| `electrical.displays.raymarine.group3.brightness` | `Group3 Group 3 Brightness` | `ratio` |
| `electrical.displays.raymarine.group3.color` | `Group 3 Color` | `` |
| `electrical.displays.raymarine.group4.brightness` | `Group4 Group 4 Brightness` | `ratio` |
| `electrical.displays.raymarine.group4.color` | `Group 4 Color` | `` |
| `electrical.displays.raymarine.group5.brightness` | `Group5 Group 5 Brightness` | `ratio` |
| `electrical.displays.raymarine.group5.color` | `Group 5 Color` | `` |
| `electrical.displays.raymarine.helm1.brightness` | `Helm 1 Brightness` | `ratio` |
| `electrical.displays.raymarine.helm1.color` | `Helm 1 Color` | `` |
| `electrical.displays.raymarine.helm1.nightMode.state` | `Raymarine Helm 1 Night Mode` | `bool` |
| `electrical.displays.raymarine.helm2.brightness` | `Helm 2 Brightness` | `ratio` |
| `electrical.displays.raymarine.helm2.color` | `Helm 2 Color` | `` |
| `electrical.displays.raymarine.mast.brightness` | `Mast Brightness` | `ratio` |
| `electrical.displays.raymarine.mast.color` | `Mast Color` | `` |
| `electrical.displays.raymarine.none.brightness` | `None Brightness` | `ratio` |
| `electrical.displays.raymarine.none.color` | `None Color` | `` |
| `entertainment.device.fusion1.state` | `Entertainment Device Fusion1 State` | `` |
| `environment.current.drift` | `Current Drift` | `` |
| `environment.current.driftImpact` | `Current Drift Impact` | `` |
| `environment.current.setMagnetic` | `Current Set Magnetic` | `` |
| `environment.current.setTrue` | `Current Set True` | `` |
| `environment.depth.transducerToKeel` | `Depth Transducer To Keel` | `m` |
| `environment.inside.airquality` | `Inside Airquality` | `` |
| `environment.inside.gas` | `Inside Gas` | `` |
| `environment.inside.humidity` | `Inside Humidity` | `` |
| `environment.inside.pressure` | `Inside Pressure` | `hPa` |
| `environment.inside.temperature` | `Inside Temperature` | `degC` |
| `environment.water.temperature` | `Water Temperature` | `degC` |
| `environment.wind.angleApparent` | `AWA` | `°` |
| `environment.wind.angleTrueGround` | `TWA Ground` | `°` |
| `environment.wind.angleTrueWater` | `TWA` | `°` |
| `environment.wind.directionTrue` | `GWD` | `° T` |
| `environment.wind.speedApparent` | `AWS` | `kn` |
| `environment.wind.speedOverGround` | `GWS` | `kn` |
| `environment.wind.speedTrue` | `TWS` | `kn` |
| `navigation.course.calcValues.bearingMagnetic` | `Course Calc Values Bearing Magnetic` | `° M` |
| `navigation.course.calcValues.bearingTrackMagnetic` | `Course Calc Values Bearing Track Magnetic` | `° M` |
| `navigation.course.calcValues.bearingTrackTrue` | `Course Calc Values Bearing Track True` | `° T` |
| `navigation.course.calcValues.bearingTrue` | `Course Calc Values Bearing True` | `° T` |
| `navigation.course.calcValues.calcMethod` | `Course Calc Values Calc Method` | `` |
| `navigation.course.calcValues.crossTrackError` | `Course Calc Values Cross Track Error` | `m` |
| `navigation.course.calcValues.distance` | `Course Calc Values Distance` | `m` |
| `navigation.course.calcValues.estimatedTimeOfArrival` | `Course Calc Values Estimated Time Of Arrival` | `` |
| `navigation.course.calcValues.previousPoint.distance` | `Course Calc Values Previous Point Distance` | `m` |
| `navigation.course.calcValues.route.distance` | `Course Calc Values Route Distance` | `m` |
| `navigation.course.calcValues.route.estimatedTimeOfArrival` | `Course Calc Values Route Estimated Time Of Arrival` | `` |
| `navigation.course.calcValues.route.timeToGo` | `Course Calc Values Route Time To Go` | `s` |
| `navigation.course.calcValues.targetSpeed` | `Course Calc Values Target Speed` | `m/s` |
| `navigation.course.calcValues.timeToGo` | `Course Calc Values Time To Go` | `s` |
| `navigation.course.calcValues.velocityMadeGood` | `Course Calc Values Velocity Made Good` | `m/s` |
| `navigation.courseGreatCircle.activeRoute.startTime` | `Course Great Circle Active Route Start Time` | `` |
| `navigation.courseGreatCircle.bearingTrackTrue` | `Course Great Circle Bearing Track True` | `° T` |
| `navigation.courseGreatCircle.crossTrackError` | `Course Great Circle Cross Track Error` | `m` |
| `navigation.courseGreatCircle.nextPoint.arrivalCircle` | `Course Great Circle Next Point Arrival Circle` | `` |
| `navigation.courseGreatCircle.nextPoint.bearingTrue` | `Course Great Circle Next Point Bearing True` | `° T` |
| `navigation.courseGreatCircle.nextPoint.distance` | `Course Great Circle Next Point Distance` | `m` |
| `navigation.courseGreatCircle.nextPoint.timeToGo` | `Course Great Circle Next Point Time To Go` | `s` |
| `navigation.courseGreatCircle.nextPoint.velocityMadeGood` | `Course Great Circle Next Point Velocity Made Good` | `m/s` |
| `navigation.courseOverGroundMagnetic` | `COG Magnetic` | `° M` |
| `navigation.courseOverGroundTrue` | `COG` | `° T` |
| `navigation.courseRhumbline.activeRoute.startTime` | `Course Rhumbline Active Route Start Time` | `` |
| `navigation.courseRhumbline.nextPoint.arrivalCircle` | `Course Rhumbline Next Point Arrival Circle` | `` |
| `navigation.currentRoute.name` | `Current Route Name` | `` |
| `navigation.datetime` | `Datetime` | `` |
| `navigation.gnss.antennaAltitude` | `Gnss Antenna Altitude` | `m` |
| `navigation.gnss.geoidalSeparation` | `Gnss Geoidal Separation` | `` |
| `navigation.gnss.horizontalDilution` | `Gnss Horizontal Dilution` | `` |
| `navigation.gnss.integrity` | `Gnss Integrity` | `` |
| `navigation.gnss.methodQuality` | `Gnss Method Quality` | `` |
| `navigation.gnss.satellites` | `Gnss Satellites` | `` |
| `navigation.gnss.type` | `Gnss Type` | `` |
| `navigation.headingMagnetic` | `HDM` | `° M` |
| `navigation.headingTrue` | `HDT` | `° T` |
| `navigation.leewayAngle` | `Leeway Angle` | `°` |
| `navigation.log` | `Log` | `m` |
| `navigation.magneticVariation` | `Magnetic Variation` | `°` |
| `navigation.position` | `Position` | `` |
| `navigation.rateOfTurn` | `Rate Of Turn` | `rad/s` |
| `navigation.speedOverGround` | `SOG` | `kn` |
| `navigation.speedThroughWater` | `STW` | `kn` |
| `navigation.speedThroughWaterReferenceType` | `Speed Through Water Reference Type` | `` |
| `navigation.trip.log` | `Trip Log` | `m` |
| `noforeignland.savepoint` | `Noforeignland Savepoint` | `` |
| `noforeignland.savepoint_local` | `Noforeignland Savepoint local` | `` |
| `noforeignland.sent_to_api` | `Noforeignland Sent to api` | `` |
| `noforeignland.sent_to_api_local` | `Noforeignland Sent to api local` | `` |
| `noforeignland.status` | `Noforeignland Status` | `` |
| `noforeignland.status_boolean` | `Noforeignland Status boolean` | `` |
| `performance.gybeAngle` | `Gybe Angle` | `°` |
| `performance.gybeAngleTargetSpeed` | `Gybe Angle Target Speed` | `m/s` |
| `performance.gybeAngleVelocityMadeGood` | `Gybe Angle Velocity Made Good` | `m/s` |
| `performance.leeway` | `Leeway` | `°` |
| `performance.polarSpeed` | `Polar Speed` | `m/s` |
| `performance.polarSpeedRatio` | `Polar Speed Ratio` | `ratio` |
| `performance.targetAngle` | `Target Angle` | `°` |
| `performance.targetSpeed` | `Target Speed` | `m/s` |
| `performance.velocityMadeGood` | `Velocity Made Good` | `m/s` |
| `performance.velocityMadeGoodToWaypoint` | `Velocity Made Good To Waypoint` | `m/s` |
| `sensors.ais.class` | `Ais Class` | `` |
| `sensors.ais.fromBow` | `Ais From Bow` | `` |
| `sensors.ais.fromCenter` | `Ais From Center` | `` |
| `sensors.gps.fromBow` | `Gps From Bow` | `` |
| `steering.autopilot.state` | `Autopilot State` | `` |
| `steering.autopilot.target.headingMagnetic` | `Autopilot Target Heading Magnetic` | `° M` |
| `steering.autopilot.target.windAngleApparent` | `Autopilot Target Wind Angle Apparent` | `°` |
| `steering.rudderAngle` | `Rudder Angle` | `°` |
