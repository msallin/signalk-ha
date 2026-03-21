"""Signal K schema metadata used to enrich discovery."""

from __future__ import annotations

from dataclasses import dataclass

# Signal K schema metadata used for UX enrichment.
# Generated from Signal K schema version 1.7.1.
# Update SCHEMA_VERSION and entries together when adopting a new spec version.
SCHEMA_VERSION = "1.7.1"

SCHEMA_GROUPS = (
    "communication",
    "design",
    "electrical",
    "environment",
    "navigation",
    "notifications",
    "performance",
    "propulsion",
    "resources",
    "sails",
    "sensors",
    "sources",
    "steering",
    "tanks",
)


@dataclass(frozen=True)
class SchemaEntry:
    description: str | None = None
    units: str | None = None


_EXACT_ENTRIES: dict[str, SchemaEntry] = {
    "communication.callsignHf": SchemaEntry(
        description="Callsign for HF communication",
    ),
    "communication.callsignVhf": SchemaEntry(
        description="Callsign for VHF communication",
    ),
    "communication.crewNames": SchemaEntry(
        description="Array with the names of the crew",
    ),
    "communication.email": SchemaEntry(
        description="Regular email for the skipper",
    ),
    "communication.emailHf": SchemaEntry(
        description=("Email address to be used for HF email (Winmail, Airmail, Sailmail) "),
    ),
    "communication.phoneNumber": SchemaEntry(
        description="Phone number of skipper",
    ),
    "communication.satPhoneNumber": SchemaEntry(
        description="Satellite phone number for vessel.",
    ),
    "communication.skipperName": SchemaEntry(
        description="Full name of the skipper of the vessel.",
    ),
    "design.airHeight": SchemaEntry(
        description="Total height of the vessel",
        units="m",
    ),
    "design.aisShipType": SchemaEntry(
        description=("The ais ship type see http://www.bosunsmate.org/ais/message5.php "),
    ),
    "design.beam": SchemaEntry(
        description="Beam length",
        units="m",
    ),
    "design.displacement": SchemaEntry(
        description="The displacement of the vessel",
        units="kg",
    ),
    "design.draft": SchemaEntry(
        description="The draft of the vessel",
    ),
    "design.keel": SchemaEntry(
        description="Information about the vessel's keel",
    ),
    "design.keel.angle": SchemaEntry(
        description=(
            "A number indicating at which angle the keel currently is (in "
            "case of a canting keel), negative to port. "
        ),
        units="rad",
    ),
    "design.keel.lift": SchemaEntry(
        description=(
            "In the case of a lifting keel, centreboard or daggerboard, "
            "the part of the keel which is extended. 0 is 'all the way "
            "up' and 1 is 'all the way down'. 0.8 would be 80% down. "
        ),
        units="ratio",
    ),
    "design.keel.type": SchemaEntry(
        description="The type of keel.",
    ),
    "design.length": SchemaEntry(
        description="The various lengths of the vessel",
    ),
    "design.rigging": SchemaEntry(
        description="Information about the vessel's rigging",
    ),
    "design.rigging.configuration": SchemaEntry(
        description="The configuration of the rigging",
    ),
    "design.rigging.masts": SchemaEntry(
        description="The number of masts on the vessel.",
    ),
    "electrical.ac": SchemaEntry(
        description="AC buses",
    ),
    "electrical.alternators": SchemaEntry(
        description="Data about an Alternator charging device",
    ),
    "electrical.batteries": SchemaEntry(
        description="Data about the vessel's batteries",
    ),
    "electrical.chargers": SchemaEntry(
        description="Data about AC sourced battery charger",
    ),
    "electrical.inverters": SchemaEntry(
        description="Data about the Inverter that has both DC and AC qualities",
    ),
    "electrical.solar": SchemaEntry(
        description="Data about Solar charging device(s)",
    ),
    "environment.current": SchemaEntry(
        description="Direction and strength of current affecting the vessel",
    ),
    "environment.depth": SchemaEntry(
        description="Depth related data",
    ),
    "environment.depth.belowKeel": SchemaEntry(
        description="Depth below keel",
        units="m",
    ),
    "environment.depth.belowSurface": SchemaEntry(
        description="Depth from surface",
        units="m",
    ),
    "environment.depth.belowTransducer": SchemaEntry(
        description="Depth below Transducer",
        units="m",
    ),
    "environment.depth.surfaceToTransducer": SchemaEntry(
        description="Depth transducer is below the water surface",
        units="m",
    ),
    "environment.depth.transducerToKeel": SchemaEntry(
        description="Depth from the transducer to the bottom of the keel",
        units="m",
    ),
    "environment.heave": SchemaEntry(
        description="Vertical movement of the vessel due to waves",
        units="m",
    ),
    "environment.inside": SchemaEntry(
        description="Environmental conditions inside the vessel's hull",
    ),
    "environment.inside.airDensity": SchemaEntry(
        description="Air density in zone",
        units="kg/m3",
    ),
    "environment.inside.dewPoint": SchemaEntry(
        description="DEPRECATED: use dewPointTemperature",
        units="K",
    ),
    "environment.inside.dewPointTemperature": SchemaEntry(
        description="Dewpoint in zone",
        units="K",
    ),
    "environment.inside.heatIndexTemperature": SchemaEntry(
        description="Current heat index temperature in zone",
        units="K",
    ),
    "environment.inside.illuminance": SchemaEntry(
        description="Illuminance in zone",
        units="Lux",
    ),
    "environment.inside.pressure": SchemaEntry(
        description="Pressure in zone",
        units="Pa",
    ),
    "environment.inside.relativeHumidity": SchemaEntry(
        description="Relative humidity in zone",
        units="ratio",
    ),
    "environment.inside.temperature": SchemaEntry(
        description="Temperature",
        units="K",
    ),
    "environment.mode": SchemaEntry(
        description=(
            "Mode of the vessel based on the current conditions. Can be "
            "combined with navigation.state to control vessel signals eg "
            "switch to night mode for instrumentation and lights, or make "
            "sound signals for fog. "
        ),
    ),
    "environment.outside": SchemaEntry(
        description="Environmental conditions outside of the vessel's hull",
    ),
    "environment.outside.airDensity": SchemaEntry(
        description="Current outside air density",
        units="kg/m3",
    ),
    "environment.outside.apparentWindChillTemperature": SchemaEntry(
        description="Current outside apparent wind chill temperature",
        units="K",
    ),
    "environment.outside.dewPointTemperature": SchemaEntry(
        description="Current outside dew point temperature",
        units="K",
    ),
    "environment.outside.heatIndexTemperature": SchemaEntry(
        description="Current outside heat index temperature",
        units="K",
    ),
    "environment.outside.humidity": SchemaEntry(
        description="DEPRECATED: use relativeHumidity",
        units="ratio",
    ),
    "environment.outside.illuminance": SchemaEntry(
        description="Current outside ambient light flux.",
        units="Lux",
    ),
    "environment.outside.pressure": SchemaEntry(
        description="Current outside air ambient pressure",
        units="Pa",
    ),
    "environment.outside.relativeHumidity": SchemaEntry(
        description="Current outside air relative humidity",
        units="ratio",
    ),
    "environment.outside.temperature": SchemaEntry(
        description="Current outside air temperature",
        units="K",
    ),
    "environment.outside.theoreticalWindChillTemperature": SchemaEntry(
        description="Current outside theoretical wind chill temperature",
        units="K",
    ),
    "environment.tide": SchemaEntry(
        description="Tide data",
    ),
    "environment.tide.heightHigh": SchemaEntry(
        description=(
            "Next high tide height  relative to lowest astronomical tide (LAT/Chart Datum) "
        ),
        units="m",
    ),
    "environment.tide.heightLow": SchemaEntry(
        description=(
            "The next low tide height relative to lowest astronomical tide (LAT/Chart Datum) "
        ),
        units="m",
    ),
    "environment.tide.heightNow": SchemaEntry(
        description=(
            "The current tide height  relative to lowest astronomical tide (LAT/Chart Datum) "
        ),
        units="m",
    ),
    "environment.tide.timeHigh": SchemaEntry(
        description="Time of next high tide in UTC",
    ),
    "environment.tide.timeLow": SchemaEntry(
        description="Time of the next low tide in UTC",
    ),
    "environment.time": SchemaEntry(
        description=(
            "A time reference for the vessel. All clocks on the vessel "
            "dispaying local time should use the timezone offset here. If "
            "a timezoneRegion is supplied the timezone must also be "
            "supplied. If timezoneRegion is supplied that should be "
            "displayed by UIs in preference to simply timezone. ie 12:05 "
            "(Europe/London) should be displayed in preference to 12:05 "
            "(UTC+01:00) "
        ),
    ),
    "environment.time.millis": SchemaEntry(
        description="Milliseconds since the UNIX epoch (1970-01-01 00:00:00)",
    ),
    "environment.time.timezoneOffset": SchemaEntry(
        description=(
            "Onboard timezone offset from UTC in hours and minutes "
            "(-)hhmm. +ve means east of Greenwich. For use by UIs "
        ),
    ),
    "environment.time.timezoneRegion": SchemaEntry(
        description=(
            "Onboard timezone offset as listed in the IANA timezone database (tz database) "
        ),
    ),
    "environment.water": SchemaEntry(
        description=("Environmental conditions of the water that the vessel is sailing in "),
    ),
    "environment.water.salinity": SchemaEntry(
        description="Water salinity",
        units="ratio",
    ),
    "environment.water.temperature": SchemaEntry(
        description="Current water temperature",
        units="K",
    ),
    "environment.wind": SchemaEntry(
        description="Wind data.",
    ),
    "environment.wind.angleApparent": SchemaEntry(
        description="Apparent wind angle, negative to port",
        units="rad",
    ),
    "environment.wind.angleTrueGround": SchemaEntry(
        description="True wind angle based on speed over ground, negative to port",
        units="rad",
    ),
    "environment.wind.angleTrueWater": SchemaEntry(
        description=("True wind angle based on speed through water, negative to port "),
        units="rad",
    ),
    "environment.wind.directionChangeAlarm": SchemaEntry(
        description="The angle the wind needs to shift to raise an alarm",
        units="rad",
    ),
    "environment.wind.directionMagnetic": SchemaEntry(
        description="The wind direction relative to magnetic north",
        units="rad",
    ),
    "environment.wind.directionTrue": SchemaEntry(
        description="The wind direction relative to true north",
        units="rad",
    ),
    "environment.wind.speedApparent": SchemaEntry(
        description="Apparent wind speed",
        units="m/s",
    ),
    "environment.wind.speedOverGround": SchemaEntry(
        description=(
            "Wind speed over ground (as calculated from speedApparent and "
            "vessel's speed over ground) "
        ),
        units="m/s",
    ),
    "environment.wind.speedTrue": SchemaEntry(
        description=(
            "Wind speed over water (as calculated from speedApparent and "
            "vessel's speed through water) "
        ),
        units="m/s",
    ),
    "navigation.anchor": SchemaEntry(
        description="The anchor data, for anchor watch etc",
    ),
    "navigation.anchor.currentRadius": SchemaEntry(
        description="Current distance to anchor",
        units="m",
    ),
    "navigation.anchor.maxRadius": SchemaEntry(
        description=(
            "Radius of anchor alarm boundary. The distance from anchor to the center of the boat "
        ),
        units="m",
    ),
    "navigation.anchor.position": SchemaEntry(
        description=(
            "The actual anchor position of the vessel in 3 dimensions, "
            "probably an estimate at best "
        ),
    ),
    "navigation.attitude": SchemaEntry(
        description="Vessel attitude: roll, pitch and yaw",
    ),
    "navigation.closestApproach": SchemaEntry(
        description="Calculated values for other vessels, e.g. from AIS",
    ),
    "navigation.courseGreatCircle": SchemaEntry(
        description="Course information computed with Great Circle",
    ),
    "navigation.courseGreatCircle.activeRoute": SchemaEntry(
        description=("Data required if sailing to an active route, defined in resources. "),
    ),
    "navigation.courseGreatCircle.activeRoute.estimatedTimeOfArrival": SchemaEntry(
        description=("The estimated time of arrival at the end of the current route "),
    ),
    "navigation.courseGreatCircle.activeRoute.startTime": SchemaEntry(
        description="The time this route was activated",
    ),
    "navigation.courseGreatCircle.bearingTrackMagnetic": SchemaEntry(
        description=(
            "The bearing of a line between previousPoint and nextPoint, "
            "relative to magnetic north. "
        ),
        units="rad",
    ),
    "navigation.courseGreatCircle.bearingTrackTrue": SchemaEntry(
        description=(
            "The bearing of a line between previousPoint and nextPoint, relative to true north. "
        ),
        units="rad",
    ),
    "navigation.courseGreatCircle.crossTrackError": SchemaEntry(
        description=(
            "The distance from the vessel's present position to the "
            "closest point on a line (track) between previousPoint and "
            "nextPoint. A negative number indicates that the vessel is "
            "currently to the left of this line (and thus must steer "
            "right to compensate), a positive number means the vessel is "
            "to the right of the line (steer left to compensate). "
        ),
        units="m",
    ),
    "navigation.courseGreatCircle.nextPoint": SchemaEntry(
        description="The point on earth the vessel's presently navigating towards",
    ),
    "navigation.courseGreatCircle.nextPoint.bearingMagnetic": SchemaEntry(
        description=(
            "The bearing of a line between the vessel's current position "
            "and nextPoint, relative to magnetic north "
        ),
        units="rad",
    ),
    "navigation.courseGreatCircle.nextPoint.bearingTrue": SchemaEntry(
        description=(
            "The bearing of a line between the vessel's current position "
            "and nextPoint, relative to true north "
        ),
        units="rad",
    ),
    "navigation.courseGreatCircle.nextPoint.distance": SchemaEntry(
        description=(
            "The distance in meters between the vessel's present position and the nextPoint "
        ),
        units="m",
    ),
    "navigation.courseGreatCircle.nextPoint.estimatedTimeOfArrival": SchemaEntry(
        description="The estimated time of arrival at nextPoint position",
    ),
    "navigation.courseGreatCircle.nextPoint.position": SchemaEntry(
        description="The position of nextPoint in two dimensions",
    ),
    "navigation.courseGreatCircle.nextPoint.timeToGo": SchemaEntry(
        description=(
            "Time in seconds to reach nextPoint's perpendicular) with current speed & direction "
        ),
        units="s",
    ),
    "navigation.courseGreatCircle.nextPoint.velocityMadeGood": SchemaEntry(
        description="The velocity component of the vessel towards the nextPoint",
        units="m/s",
    ),
    "navigation.courseGreatCircle.previousPoint": SchemaEntry(
        description="The point on earth the vessel's presently navigating from",
    ),
    "navigation.courseGreatCircle.previousPoint.distance": SchemaEntry(
        description=(
            "The distance in meters between previousPoint and the vessel's present position "
        ),
        units="m",
    ),
    "navigation.courseGreatCircle.previousPoint.position": SchemaEntry(
        description="The position of lastPoint in two dimensions",
    ),
    "navigation.courseOverGroundMagnetic": SchemaEntry(
        description="Course over ground (magnetic)",
        units="rad",
    ),
    "navigation.courseOverGroundTrue": SchemaEntry(
        description="Course over ground (true)",
        units="rad",
    ),
    "navigation.courseRhumbline": SchemaEntry(
        description="Course information computed with Rhumbline",
    ),
    "navigation.courseRhumbline.activeRoute": SchemaEntry(
        description=("Data required if sailing to an active route, defined in resources. "),
    ),
    "navigation.courseRhumbline.activeRoute.estimatedTimeOfArrival": SchemaEntry(
        description=("The estimated time of arrival at the end of the current route "),
    ),
    "navigation.courseRhumbline.activeRoute.startTime": SchemaEntry(
        description="The time this route was activated",
    ),
    "navigation.courseRhumbline.bearingTrackMagnetic": SchemaEntry(
        description=(
            "The bearing of a line between previousPoint and nextPoint, "
            "relative to magnetic north. "
        ),
        units="rad",
    ),
    "navigation.courseRhumbline.bearingTrackTrue": SchemaEntry(
        description=(
            "The bearing of a line between previousPoint and nextPoint, relative to true north. "
        ),
        units="rad",
    ),
    "navigation.courseRhumbline.crossTrackError": SchemaEntry(
        description=(
            "The distance from the vessel's present position to the "
            "closest point on a line (track) between previousPoint and "
            "nextPoint. A negative number indicates that the vessel is "
            "currently to the left of this line (and thus must steer "
            "right to compensate), a positive number means the vessel is "
            "to the right of the line (steer left to compensate). "
        ),
        units="m",
    ),
    "navigation.courseRhumbline.nextPoint": SchemaEntry(
        description="The point on earth the vessel's presently navigating towards",
    ),
    "navigation.courseRhumbline.nextPoint.bearingMagnetic": SchemaEntry(
        description=(
            "The bearing of a line between the vessel's current position "
            "and nextPoint, relative to magnetic north "
        ),
        units="rad",
    ),
    "navigation.courseRhumbline.nextPoint.bearingTrue": SchemaEntry(
        description=(
            "The bearing of a line between the vessel's current position "
            "and nextPoint, relative to true north "
        ),
        units="rad",
    ),
    "navigation.courseRhumbline.nextPoint.distance": SchemaEntry(
        description=(
            "The distance in meters between the vessel's present position and the nextPoint "
        ),
        units="m",
    ),
    "navigation.courseRhumbline.nextPoint.estimatedTimeOfArrival": SchemaEntry(
        description="The estimated time of arrival at nextPoint position",
    ),
    "navigation.courseRhumbline.nextPoint.position": SchemaEntry(
        description="The position of nextPoint in two dimensions",
    ),
    "navigation.courseRhumbline.nextPoint.timeToGo": SchemaEntry(
        description=(
            "Time in seconds to reach nextPoint's perpendicular) with current speed & direction "
        ),
        units="s",
    ),
    "navigation.courseRhumbline.nextPoint.velocityMadeGood": SchemaEntry(
        description="The velocity component of the vessel towards the nextPoint",
        units="m/s",
    ),
    "navigation.courseRhumbline.previousPoint": SchemaEntry(
        description="The point on earth the vessel's presently navigating from",
    ),
    "navigation.courseRhumbline.previousPoint.distance": SchemaEntry(
        description=(
            "The distance in meters between previousPoint and the vessel's present position "
        ),
        units="m",
    ),
    "navigation.courseRhumbline.previousPoint.position": SchemaEntry(
        description="The position of lastPoint in two dimensions",
    ),
    "navigation.datetime": SchemaEntry(
        description="Time and Date from the GNSS Positioning System",
    ),
    "navigation.datetime.gnssTimeSource": SchemaEntry(
        description="Source of GNSS Date and Time",
    ),
    "navigation.destination": SchemaEntry(
        description="The intended destination of this trip",
    ),
    "navigation.destination.commonName": SchemaEntry(
        description=("Common name of the Destination, eg 'Fiji', also used in ais messages "),
    ),
    "navigation.destination.eta": SchemaEntry(
        description="Expected time of arrival at destination waypoint",
    ),
    "navigation.destination.waypoint": SchemaEntry(
        description="UUID of destination waypoint",
    ),
    "navigation.gnss": SchemaEntry(
        description="Global satellite navigation meta information",
    ),
    "navigation.gnss.antennaAltitude": SchemaEntry(
        description="Altitude of antenna",
        units="m",
    ),
    "navigation.gnss.differentialAge": SchemaEntry(
        description="Age of DGPS data",
        units="s",
    ),
    "navigation.gnss.differentialReference": SchemaEntry(
        description="ID of DGPS base station",
    ),
    "navigation.gnss.geoidalSeparation": SchemaEntry(
        description="Difference between WGS84 earth ellipsoid and mean sea level",
    ),
    "navigation.gnss.horizontalDilution": SchemaEntry(
        description="Horizontal Dilution of Precision",
    ),
    "navigation.gnss.integrity": SchemaEntry(
        description="Integrity of the satellite fix",
    ),
    "navigation.gnss.methodQuality": SchemaEntry(
        description="Quality of the satellite fix",
    ),
    "navigation.gnss.positionDilution": SchemaEntry(
        description="Positional Dilution of Precision",
    ),
    "navigation.gnss.satellites": SchemaEntry(
        description="Number of satellites",
    ),
    "navigation.gnss.type": SchemaEntry(
        description="Fix type",
    ),
    "navigation.headingCompass": SchemaEntry(
        description=(
            "Current magnetic heading received from the compass. This is "
            "not adjusted for magneticDeviation of the compass "
        ),
        units="rad",
    ),
    "navigation.headingMagnetic": SchemaEntry(
        description=(
            "Current magnetic heading of the vessel, equals "
            "'headingCompass adjusted for magneticDeviation' "
        ),
        units="rad",
    ),
    "navigation.headingTrue": SchemaEntry(
        description=(
            "The current true north heading of the vessel, equals "
            "'headingMagnetic adjusted for magneticVariation' "
        ),
        units="rad",
    ),
    "navigation.leewayAngle": SchemaEntry(
        description=(
            "Leeway Angle derived from the longitudinal and transverse speeds through the water "
        ),
        units="rad",
    ),
    "navigation.lights": SchemaEntry(
        description="Current state of the vessels navigation lights",
    ),
    "navigation.log": SchemaEntry(
        description="Total distance traveled",
        units="m",
    ),
    "navigation.magneticDeviation": SchemaEntry(
        description=("Magnetic deviation of the compass at the current headingCompass "),
        units="rad",
    ),
    "navigation.magneticVariation": SchemaEntry(
        description=(
            "The magnetic variation (declination) at the current position "
            "that must be added to the magnetic heading to derive the "
            "true heading. Easterly variations are positive and Westerly "
            "variations are negative (in Radians). "
        ),
        units="rad",
    ),
    "navigation.magneticVariationAgeOfService": SchemaEntry(
        description=("Seconds since the 1st Jan 1970 that the variation calculation was made "),
        units="s",
    ),
    "navigation.maneuver": SchemaEntry(
        description=("Special maneuver such as regional passing arrangement. (from ais) "),
    ),
    "navigation.position": SchemaEntry(
        description=("The position of the vessel in 2 or 3 dimensions (WGS84 datum) "),
    ),
    "navigation.racing": SchemaEntry(
        description="Specific navigational data related to yacht racing.",
    ),
    "navigation.racing.distanceStartline": SchemaEntry(
        description="The current distance to the start line",
        units="m",
    ),
    "navigation.racing.layline": SchemaEntry(
        description="The layline crossing the current course",
    ),
    "navigation.racing.layline.distance": SchemaEntry(
        description="The current distance to the layline",
        units="m",
    ),
    "navigation.racing.layline.time": SchemaEntry(
        description="The time to the layline at current speed and heading",
        units="s",
    ),
    "navigation.racing.oppositeLayline": SchemaEntry(
        description="The layline parallell to current course",
    ),
    "navigation.racing.oppositeLayline.distance": SchemaEntry(
        description="The current distance to the layline",
        units="m",
    ),
    "navigation.racing.oppositeLayline.time": SchemaEntry(
        description="The time to the layline at current speed and heading",
        units="s",
    ),
    "navigation.racing.startLinePort": SchemaEntry(
        description="Position of port start mark",
    ),
    "navigation.racing.startLineStb": SchemaEntry(
        description="Position of starboard start mark",
    ),
    "navigation.racing.timePortDown": SchemaEntry(
        description="Time to arrive at the start line on port, turning downwind",
        units="s",
    ),
    "navigation.racing.timePortUp": SchemaEntry(
        description="Time to arrive at the start line on port, turning upwind",
        units="s",
    ),
    "navigation.racing.timeStbdDown": SchemaEntry(
        description=("Time to arrive at the start line on starboard, turning downwind "),
        units="s",
    ),
    "navigation.racing.timeStbdUp": SchemaEntry(
        description=("Time to arrive at the start line on starboard, turning upwind "),
        units="s",
    ),
    "navigation.racing.timeToStart": SchemaEntry(
        description="Time left before start",
        units="s",
    ),
    "navigation.rateOfTurn": SchemaEntry(
        description=(
            "Rate of turn (+ve is change to starboard). If the value is "
            "AIS RIGHT or LEFT, set to +-0.0206 rads and add warning in "
            "notifications "
        ),
        units="rad/s",
    ),
    "navigation.speedOverGround": SchemaEntry(
        description=(
            "Vessel speed over ground. If converting from AIS 'HIGH' "
            "value, set to 102.2 (Ais max value) and add warning in "
            "notifications "
        ),
        units="m/s",
    ),
    "navigation.speedThroughWater": SchemaEntry(
        description="Vessel speed through the water",
        units="m/s",
    ),
    "navigation.speedThroughWaterLongitudinal": SchemaEntry(
        description="Longitudinal speed through the water",
        units="m/s",
    ),
    "navigation.speedThroughWaterTransverse": SchemaEntry(
        description="Transverse speed through the water (Leeway)",
        units="m/s",
    ),
    "navigation.state": SchemaEntry(
        description="Current navigational state of the vessel",
    ),
    "navigation.trip": SchemaEntry(
        description="Trip data",
    ),
    "navigation.trip.lastReset": SchemaEntry(
        description="Trip log reset time",
    ),
    "navigation.trip.log": SchemaEntry(
        description="Total distance traveled on this trip / since trip reset",
        units="m",
    ),
    "performance.activePolar": SchemaEntry(
        description="The UUID of the active polar table",
    ),
    "performance.activePolarData": SchemaEntry(
        description="The 'polar' object belonging to the selected 'activePolar'",
    ),
    "performance.beatAngle": SchemaEntry(
        description=(
            "The true wind beat angle for the best velocity made good "
            "based on current current polar diagram and WindSpeedTrue. "
        ),
        units="rad",
    ),
    "performance.beatAngleTargetSpeed": SchemaEntry(
        description="The target speed for the beat angle.",
        units="m/s",
    ),
    "performance.beatAngleVelocityMadeGood": SchemaEntry(
        description="The velocity made good for the beat angle.",
        units="m/s",
    ),
    "performance.gybeAngle": SchemaEntry(
        description=(
            "The true wind gybe angle for the best velocity made good "
            "downwind based on current polar diagram and WindSpeedTrue. "
        ),
        units="rad",
    ),
    "performance.gybeAngleTargetSpeed": SchemaEntry(
        description="The target speed for the gybe angle.",
        units="m/s",
    ),
    "performance.gybeAngleVelocityMadeGood": SchemaEntry(
        description="The velocity made good for the gybe angle",
        units="m/s",
    ),
    "performance.leeway": SchemaEntry(
        description="Current leeway",
        units="rad",
    ),
    "performance.polarSpeed": SchemaEntry(
        description=(
            "The current polar speed based on current polar diagram, "
            "WindSpeedTrue and angleTrueWater. "
        ),
        units="m/s",
    ),
    "performance.polarSpeedRatio": SchemaEntry(
        description="The ratio of current speed through water to the polar speed.",
        units="ratio",
    ),
    "performance.polars": SchemaEntry(
        description="Polar objects",
    ),
    "performance.tackMagnetic": SchemaEntry(
        description="Magnetic heading on opposite tack.",
        units="rad",
    ),
    "performance.tackTrue": SchemaEntry(
        description="True heading on opposite tack.",
        units="rad",
    ),
    "performance.targetAngle": SchemaEntry(
        description=(
            "The true wind gybe or beat angle for the best velocity made "
            "good downwind or upwind based on current polar diagram and "
            "WindSpeedTrue. "
        ),
        units="rad",
    ),
    "performance.targetSpeed": SchemaEntry(
        description=(
            "The target speed for the beat angle or gybe angle, which ever is applicable. "
        ),
        units="m/s",
    ),
    "performance.velocityMadeGood": SchemaEntry(
        description=(
            "The current velocity made good derived from the speed "
            "through water and appearant wind angle. A positive value is "
            "heading upwind, negative downwind. "
        ),
        units="m/s",
    ),
    "performance.velocityMadeGoodToWaypoint": SchemaEntry(
        description=(
            "The current velocity made good to the next waypoint derived "
            "from the speedOverGround, courseOverGround. "
        ),
        units="m/s",
    ),
    "resources.charts": SchemaEntry(
        description="A holder for charts, each named with their chart code",
    ),
    "resources.notes": SchemaEntry(
        description=(
            "A holder for notes about regions, each named with a UUID. "
            "Notes might include navigation or cruising info, images, or "
            "anything "
        ),
    ),
    "resources.regions": SchemaEntry(
        description="A holder for regions, each named with UUID",
    ),
    "resources.routes": SchemaEntry(
        description="A holder for routes, each named with a UUID",
    ),
    "resources.waypoints": SchemaEntry(
        description="A holder for waypoints, each named with a UUID",
    ),
    "sails.area": SchemaEntry(
        description="An object containing information about the vessels' sails.",
    ),
    "sails.area.active": SchemaEntry(
        description="The total area of the sails currently in use on the vessel",
        units="m2",
    ),
    "sails.area.total": SchemaEntry(
        description="The total area of all sails on the vessel",
        units="m2",
    ),
    "sails.inventory": SchemaEntry(
        description=(
            "An object containing a description of each sail available to the vessel crew "
        ),
    ),
    "sensors.class": SchemaEntry(
        description="AIS transponder class in sensors.ais.class, A or B",
    ),
    "sensors.fromBow": SchemaEntry(
        description="The distance from the bow to the sensor location",
    ),
    "sensors.fromCenter": SchemaEntry(
        description=(
            "The distance from the centerline to the sensor location, -ve "
            "to starboard, +ve to port "
        ),
    ),
    "sensors.name": SchemaEntry(
        description="The common name of the sensor",
    ),
    "sensors.sensorData": SchemaEntry(
        description=(
            "The data of the sensor data. FIXME - need to ref the definitions of sensor types "
        ),
    ),
    "sensors.sensorType": SchemaEntry(
        description=(
            "The datamodel definition of the sensor data. FIXME - need to "
            "create a definitions lib of sensor datamodel types "
        ),
    ),
    "steering.autopilot": SchemaEntry(
        description="Autopilot data",
    ),
    "steering.autopilot.backlash": SchemaEntry(
        description="Slack in the rudder drive mechanism",
        units="rad",
    ),
    "steering.autopilot.deadZone": SchemaEntry(
        description="Dead zone to ignore for rudder corrections",
        units="rad",
    ),
    "steering.autopilot.gain": SchemaEntry(
        description=(
            "Auto-pilot gain, higher number equals more rudder movement for a given turn "
        ),
    ),
    "steering.autopilot.maxDriveCurrent": SchemaEntry(
        description="Maximum current to use to drive servo",
        units="A",
    ),
    "steering.autopilot.maxDriveRate": SchemaEntry(
        description="Maximum rudder rotation speed",
        units="rad/s",
    ),
    "steering.autopilot.mode": SchemaEntry(
        description="Operational mode",
    ),
    "steering.autopilot.portLock": SchemaEntry(
        description="Position of servo on port lock",
        units="rad",
    ),
    "steering.autopilot.starboardLock": SchemaEntry(
        description="Position of servo on starboard lock",
        units="rad",
    ),
    "steering.autopilot.state": SchemaEntry(
        description="Autopilot state",
    ),
    "steering.autopilot.target": SchemaEntry(
        description="Autopilot target",
    ),
    "steering.autopilot.target.headingMagnetic": SchemaEntry(
        description="Target heading for autopilot, relative to Magnetic North",
        units="rad",
    ),
    "steering.autopilot.target.headingTrue": SchemaEntry(
        description="Target heading for autopilot, relative to North",
        units="rad",
    ),
    "steering.autopilot.target.windAngleApparent": SchemaEntry(
        description=("Target angle to steer, relative to Apparent wind +port -starboard "),
        units="rad",
    ),
    "steering.autopilot.target.windAngleTrue": SchemaEntry(
        description=("Target angle to steer, relative to true wind +port -starboard "),
        units="rad",
    ),
    "steering.rudderAngle": SchemaEntry(
        description="Current rudder angle, +ve is rudder to Starboard",
        units="rad",
    ),
    "steering.rudderAngleTarget": SchemaEntry(
        description=("The angle the rudder should move to, +ve is rudder to Starboard "),
        units="rad",
    ),
    "tanks.baitWell": SchemaEntry(
        description="Bait tank",
    ),
    "tanks.ballast": SchemaEntry(
        description="Ballast tanks",
    ),
    "tanks.blackWater": SchemaEntry(
        description="Black water tank (sewage)",
    ),
    "tanks.freshWater": SchemaEntry(
        description="Fresh water tank (drinking)",
    ),
    "tanks.fuel": SchemaEntry(
        description="Fuel tank (petrol or diesel)",
    ),
    "tanks.gas": SchemaEntry(
        description="Lpg/propane and other gases",
    ),
    "tanks.liveWell": SchemaEntry(
        description="Live tank (fish)",
    ),
    "tanks.lubrication": SchemaEntry(
        description="Lubrication tank (oil or grease)",
    ),
    "tanks.wasteWater": SchemaEntry(
        description="Waste water tank (grey water)",
    ),
}


_PATTERN_ENTRIES: list[tuple[tuple[str, ...], SchemaEntry]] = [
    (
        ("electrical", "ac", "*"),
        SchemaEntry(
            description="AC Bus, one or many, within the vessel",
        ),
    ),
    (
        ("electrical", "ac", "*", "dateInstalled"),
        SchemaEntry(
            description="Date device was installed",
        ),
    ),
    (
        ("electrical", "ac", "*", "location"),
        SchemaEntry(
            description="Installed location of device on vessel",
        ),
    ),
    (
        ("electrical", "ac", "*", "manufacturer", "URL"),
        SchemaEntry(
            description="Web referance / URL",
        ),
    ),
    (
        ("electrical", "ac", "*", "manufacturer", "model"),
        SchemaEntry(
            description="Model or part number",
        ),
    ),
    (
        ("electrical", "ac", "*", "manufacturer", "name"),
        SchemaEntry(
            description="Manufacturer's name",
        ),
    ),
    (
        ("electrical", "ac", "*", "name"),
        SchemaEntry(
            description=(
                "Unique ID of device (houseBattery, alternator, Generator, "
                "solar1, inverter, charger, combiner, etc.) "
            ),
        ),
    ),
    (
        ("electrical", "ac", "*", "phase"),
        SchemaEntry(
            description="Single or A,B or C in 3 Phase systems",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*"),
        SchemaEntry(
            description="AC equipment common qualities",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "apparentPower"),
        SchemaEntry(
            description="Apparent power.",
            units="W",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "associatedBus"),
        SchemaEntry(
            description="Name of BUS device is associated with",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "current"),
        SchemaEntry(
            description="RMS current",
            units="A",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "frequency"),
        SchemaEntry(
            description="AC frequency.",
            units="Hz",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "lineLineVoltage"),
        SchemaEntry(
            description="RMS voltage measured between phases",
            units="V",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "lineNeutralVoltage"),
        SchemaEntry(
            description="RMS voltage measured between phase and neutral",
            units="V",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "powerFactor"),
        SchemaEntry(
            description="Power factor",
            units="ratio",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "powerFactorLagging"),
        SchemaEntry(
            description="Lead/lag status.",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "reactivePower"),
        SchemaEntry(
            description="Reactive power",
            units="W",
        ),
    ),
    (
        ("electrical", "ac", "*", "phase", "*", "realPower"),
        SchemaEntry(
            description="Real power.",
            units="W",
        ),
    ),
    (
        ("electrical", "alternators", "*"),
        SchemaEntry(
            description="Mechanically driven alternator, includes dynamos",
        ),
    ),
    (
        ("electrical", "alternators", "*", "associatedBus"),
        SchemaEntry(
            description="Name of BUS device is associated with",
        ),
    ),
    (
        ("electrical", "alternators", "*", "chargerRole"),
        SchemaEntry(
            description=(
                "How is charging source configured?  Standalone, or in sync with another charger? "
            ),
        ),
    ),
    (
        ("electrical", "alternators", "*", "chargingAlgorithm"),
        SchemaEntry(
            description="Algorithm being used by the charger",
        ),
    ),
    (
        ("electrical", "alternators", "*", "chargingMode"),
        SchemaEntry(
            description="Charging mode i.e. float, overcharge, etc.",
        ),
    ),
    (
        ("electrical", "alternators", "*", "current"),
        SchemaEntry(
            description=(
                "Current flowing out (+ve) or in (-ve) to the device. "
                "Reversed for batteries (+ve = charging). "
            ),
            units="A",
        ),
    ),
    (
        ("electrical", "alternators", "*", "dateInstalled"),
        SchemaEntry(
            description="Date device was installed",
        ),
    ),
    (
        ("electrical", "alternators", "*", "fieldDrive"),
        SchemaEntry(
            description="% (0..100) of field voltage applied",
            units="%",
        ),
    ),
    (
        ("electrical", "alternators", "*", "location"),
        SchemaEntry(
            description="Installed location of device on vessel",
        ),
    ),
    (
        ("electrical", "alternators", "*", "manufacturer", "URL"),
        SchemaEntry(
            description="Web referance / URL",
        ),
    ),
    (
        ("electrical", "alternators", "*", "manufacturer", "model"),
        SchemaEntry(
            description="Model or part number",
        ),
    ),
    (
        ("electrical", "alternators", "*", "manufacturer", "name"),
        SchemaEntry(
            description="Manufacturer's name",
        ),
    ),
    (
        ("electrical", "alternators", "*", "name"),
        SchemaEntry(
            description=(
                "Unique ID of device (houseBattery, alternator, Generator, "
                "solar1, inverter, charger, combiner, etc.) "
            ),
        ),
    ),
    (
        ("electrical", "alternators", "*", "pulleyRatio"),
        SchemaEntry(
            description=(
                "Mechanical pulley ratio of driving source (Used to back calculate engine RPMs) "
            ),
            units="ratio",
        ),
    ),
    (
        ("electrical", "alternators", "*", "regulatorTemperature"),
        SchemaEntry(
            description="Current temperature of critical regulator components",
            units="K",
        ),
    ),
    (
        ("electrical", "alternators", "*", "revolutions"),
        SchemaEntry(
            description="Alternator revolutions per second (x60 for RPM)",
            units="Hz",
        ),
    ),
    (
        ("electrical", "alternators", "*", "setpointCurrent"),
        SchemaEntry(
            description="Target current limit",
            units="A",
        ),
    ),
    (
        ("electrical", "alternators", "*", "setpointVoltage"),
        SchemaEntry(
            description="Target regulation voltage",
            units="V",
        ),
    ),
    (
        ("electrical", "alternators", "*", "temperature"),
        SchemaEntry(
            description="Temperature measured within or on the device",
            units="K",
        ),
    ),
    (
        ("electrical", "alternators", "*", "temperature", "faultLower"),
        SchemaEntry(
            description=("Lower fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "alternators", "*", "temperature", "faultUpper"),
        SchemaEntry(
            description=("Upper fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "alternators", "*", "temperature", "warnLower"),
        SchemaEntry(
            description="Lower operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "alternators", "*", "temperature", "warnUpper"),
        SchemaEntry(
            description="Upper operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "alternators", "*", "voltage"),
        SchemaEntry(
            description="Voltage measured at or as close as possible to the device",
            units="V",
        ),
    ),
    (
        ("electrical", "alternators", "*", "voltage", "ripple"),
        SchemaEntry(
            description="DC Ripple voltage",
            units="V",
        ),
    ),
    (
        ("electrical", "batteries", "*"),
        SchemaEntry(
            description="Batteries, one or many, within the vessel",
        ),
    ),
    (
        ("electrical", "batteries", "*", "associatedBus"),
        SchemaEntry(
            description="Name of BUS device is associated with",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity"),
        SchemaEntry(
            description="Data about the battery's capacity",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity", "actual"),
        SchemaEntry(
            description=(
                "The measured capacity of battery. This may change over time "
                "and will likely deviate from the nominal capacity. "
            ),
            units="J",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity", "dischargeLimit"),
        SchemaEntry(
            description="Minimum capacity to be left in the battery while discharging",
            units="J",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity", "dischargeSinceFull"),
        SchemaEntry(
            description="Cumulative discharge since battery was last full",
            units="C",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity", "nominal"),
        SchemaEntry(
            description="The capacity of battery as specified by the manufacturer",
            units="J",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity", "remaining"),
        SchemaEntry(
            description="Capacity remaining in battery",
            units="J",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity", "stateOfCharge"),
        SchemaEntry(
            description="State of charge, 1 = 100%",
            units="ratio",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity", "stateOfHealth"),
        SchemaEntry(
            description="State of Health, 1 = 100%",
            units="ratio",
        ),
    ),
    (
        ("electrical", "batteries", "*", "capacity", "timeRemaining"),
        SchemaEntry(
            description="Time to discharge to discharge limit at current rate",
            units="s",
        ),
    ),
    (
        ("electrical", "batteries", "*", "chemistry"),
        SchemaEntry(
            description="Type of battery FLA, LiFePO4, etc.",
        ),
    ),
    (
        ("electrical", "batteries", "*", "current"),
        SchemaEntry(
            description=(
                "Current flowing out (+ve) or in (-ve) to the device. "
                "Reversed for batteries (+ve = charging). "
            ),
            units="A",
        ),
    ),
    (
        ("electrical", "batteries", "*", "dateInstalled"),
        SchemaEntry(
            description="Date device was installed",
        ),
    ),
    (
        ("electrical", "batteries", "*", "lifetimeDischarge"),
        SchemaEntry(
            description=(
                "Cumulative charge discharged from battery over operational lifetime of battery "
            ),
            units="C",
        ),
    ),
    (
        ("electrical", "batteries", "*", "lifetimeRecharge"),
        SchemaEntry(
            description=(
                "Cumulative charge recharged into battery over operational lifetime of battery "
            ),
            units="C",
        ),
    ),
    (
        ("electrical", "batteries", "*", "location"),
        SchemaEntry(
            description="Installed location of device on vessel",
        ),
    ),
    (
        ("electrical", "batteries", "*", "manufacturer", "URL"),
        SchemaEntry(
            description="Web referance / URL",
        ),
    ),
    (
        ("electrical", "batteries", "*", "manufacturer", "model"),
        SchemaEntry(
            description="Model or part number",
        ),
    ),
    (
        ("electrical", "batteries", "*", "manufacturer", "name"),
        SchemaEntry(
            description="Manufacturer's name",
        ),
    ),
    (
        ("electrical", "batteries", "*", "name"),
        SchemaEntry(
            description=(
                "Unique ID of device (houseBattery, alternator, Generator, "
                "solar1, inverter, charger, combiner, etc.) "
            ),
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature"),
        SchemaEntry(
            description="Temperature measured within or on the device",
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature", "faultLower"),
        SchemaEntry(
            description=("Lower fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature", "faultUpper"),
        SchemaEntry(
            description=("Upper fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature", "limitDischargeLower"),
        SchemaEntry(
            description="Operational minimum temperature limit for battery discharge",
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature", "limitDischargeUpper"),
        SchemaEntry(
            description="Operational maximum temperature limit for battery discharge",
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature", "limitRechargeLower"),
        SchemaEntry(
            description="Operational minimum temperature limit for battery recharging",
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature", "limitRechargeUpper"),
        SchemaEntry(
            description="Operational maximum temperature limit for battery recharging",
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature", "warnLower"),
        SchemaEntry(
            description="Lower operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "temperature", "warnUpper"),
        SchemaEntry(
            description="Upper operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "batteries", "*", "voltage"),
        SchemaEntry(
            description="Voltage measured at or as close as possible to the device",
            units="V",
        ),
    ),
    (
        ("electrical", "batteries", "*", "voltage", "ripple"),
        SchemaEntry(
            description="DC Ripple voltage",
            units="V",
        ),
    ),
    (
        ("electrical", "chargers", "*"),
        SchemaEntry(
            description="Battery charger",
        ),
    ),
    (
        ("electrical", "chargers", "*", "associatedBus"),
        SchemaEntry(
            description="Name of BUS device is associated with",
        ),
    ),
    (
        ("electrical", "chargers", "*", "chargerRole"),
        SchemaEntry(
            description=(
                "How is charging source configured?  Standalone, or in sync with another charger? "
            ),
        ),
    ),
    (
        ("electrical", "chargers", "*", "chargingAlgorithm"),
        SchemaEntry(
            description="Algorithm being used by the charger",
        ),
    ),
    (
        ("electrical", "chargers", "*", "chargingMode"),
        SchemaEntry(
            description="Charging mode i.e. float, overcharge, etc.",
        ),
    ),
    (
        ("electrical", "chargers", "*", "current"),
        SchemaEntry(
            description=(
                "Current flowing out (+ve) or in (-ve) to the device. "
                "Reversed for batteries (+ve = charging). "
            ),
            units="A",
        ),
    ),
    (
        ("electrical", "chargers", "*", "dateInstalled"),
        SchemaEntry(
            description="Date device was installed",
        ),
    ),
    (
        ("electrical", "chargers", "*", "location"),
        SchemaEntry(
            description="Installed location of device on vessel",
        ),
    ),
    (
        ("electrical", "chargers", "*", "manufacturer", "URL"),
        SchemaEntry(
            description="Web referance / URL",
        ),
    ),
    (
        ("electrical", "chargers", "*", "manufacturer", "model"),
        SchemaEntry(
            description="Model or part number",
        ),
    ),
    (
        ("electrical", "chargers", "*", "manufacturer", "name"),
        SchemaEntry(
            description="Manufacturer's name",
        ),
    ),
    (
        ("electrical", "chargers", "*", "name"),
        SchemaEntry(
            description=(
                "Unique ID of device (houseBattery, alternator, Generator, "
                "solar1, inverter, charger, combiner, etc.) "
            ),
        ),
    ),
    (
        ("electrical", "chargers", "*", "setpointCurrent"),
        SchemaEntry(
            description="Target current limit",
            units="A",
        ),
    ),
    (
        ("electrical", "chargers", "*", "setpointVoltage"),
        SchemaEntry(
            description="Target regulation voltage",
            units="V",
        ),
    ),
    (
        ("electrical", "chargers", "*", "temperature"),
        SchemaEntry(
            description="Temperature measured within or on the device",
            units="K",
        ),
    ),
    (
        ("electrical", "chargers", "*", "temperature", "faultLower"),
        SchemaEntry(
            description=("Lower fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "chargers", "*", "temperature", "faultUpper"),
        SchemaEntry(
            description=("Upper fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "chargers", "*", "temperature", "warnLower"),
        SchemaEntry(
            description="Lower operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "chargers", "*", "temperature", "warnUpper"),
        SchemaEntry(
            description="Upper operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "chargers", "*", "voltage"),
        SchemaEntry(
            description="Voltage measured at or as close as possible to the device",
            units="V",
        ),
    ),
    (
        ("electrical", "chargers", "*", "voltage", "ripple"),
        SchemaEntry(
            description="DC Ripple voltage",
            units="V",
        ),
    ),
    (
        ("electrical", "inverters", "*"),
        SchemaEntry(
            description="DC to AC inverter, one or many, within the vessel",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac"),
        SchemaEntry(
            description="AC equipment common qualities",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "apparentPower"),
        SchemaEntry(
            description="Apparent power.",
            units="W",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "associatedBus"),
        SchemaEntry(
            description="Name of BUS device is associated with",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "current"),
        SchemaEntry(
            description="RMS current",
            units="A",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "frequency"),
        SchemaEntry(
            description="AC frequency.",
            units="Hz",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "lineLineVoltage"),
        SchemaEntry(
            description="RMS voltage measured between phases",
            units="V",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "lineNeutralVoltage"),
        SchemaEntry(
            description="RMS voltage measured between phase and neutral",
            units="V",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "powerFactor"),
        SchemaEntry(
            description="Power factor",
            units="ratio",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "powerFactorLagging"),
        SchemaEntry(
            description="Lead/lag status.",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "reactivePower"),
        SchemaEntry(
            description="Reactive power",
            units="W",
        ),
    ),
    (
        ("electrical", "inverters", "*", "ac", "realPower"),
        SchemaEntry(
            description="Real power.",
            units="W",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dateInstalled"),
        SchemaEntry(
            description="Date device was installed",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc"),
        SchemaEntry(
            description="DC common qualities",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "associatedBus"),
        SchemaEntry(
            description="Name of BUS device is associated with",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "current"),
        SchemaEntry(
            description=(
                "Current flowing out (+ve) or in (-ve) to the device. "
                "Reversed for batteries (+ve = charging). "
            ),
            units="A",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "temperature"),
        SchemaEntry(
            description="Temperature measured within or on the device",
            units="K",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "temperature", "faultLower"),
        SchemaEntry(
            description=("Lower fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "temperature", "faultUpper"),
        SchemaEntry(
            description=("Upper fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "temperature", "warnLower"),
        SchemaEntry(
            description="Lower operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "temperature", "warnUpper"),
        SchemaEntry(
            description="Upper operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "voltage"),
        SchemaEntry(
            description="Voltage measured at or as close as possible to the device",
            units="V",
        ),
    ),
    (
        ("electrical", "inverters", "*", "dc", "voltage", "ripple"),
        SchemaEntry(
            description="DC Ripple voltage",
            units="V",
        ),
    ),
    (
        ("electrical", "inverters", "*", "inverterMode"),
        SchemaEntry(
            description="Mode of inverter",
        ),
    ),
    (
        ("electrical", "inverters", "*", "location"),
        SchemaEntry(
            description="Installed location of device on vessel",
        ),
    ),
    (
        ("electrical", "inverters", "*", "manufacturer", "URL"),
        SchemaEntry(
            description="Web referance / URL",
        ),
    ),
    (
        ("electrical", "inverters", "*", "manufacturer", "model"),
        SchemaEntry(
            description="Model or part number",
        ),
    ),
    (
        ("electrical", "inverters", "*", "manufacturer", "name"),
        SchemaEntry(
            description="Manufacturer's name",
        ),
    ),
    (
        ("electrical", "inverters", "*", "name"),
        SchemaEntry(
            description=(
                "Unique ID of device (houseBattery, alternator, Generator, "
                "solar1, inverter, charger, combiner, etc.) "
            ),
        ),
    ),
    (
        ("electrical", "solar", "*"),
        SchemaEntry(
            description="Photovoltaic charging devices",
        ),
    ),
    (
        ("electrical", "solar", "*", "associatedBus"),
        SchemaEntry(
            description="Name of BUS device is associated with",
        ),
    ),
    (
        ("electrical", "solar", "*", "chargerRole"),
        SchemaEntry(
            description=(
                "How is charging source configured?  Standalone, or in sync with another charger? "
            ),
        ),
    ),
    (
        ("electrical", "solar", "*", "chargingAlgorithm"),
        SchemaEntry(
            description="Algorithm being used by the charger",
        ),
    ),
    (
        ("electrical", "solar", "*", "chargingMode"),
        SchemaEntry(
            description="Charging mode i.e. float, overcharge, etc.",
        ),
    ),
    (
        ("electrical", "solar", "*", "controllerMode"),
        SchemaEntry(
            description="The current state of the engine",
        ),
    ),
    (
        ("electrical", "solar", "*", "current"),
        SchemaEntry(
            description=(
                "Current flowing out (+ve) or in (-ve) to the device. "
                "Reversed for batteries (+ve = charging). "
            ),
            units="A",
        ),
    ),
    (
        ("electrical", "solar", "*", "dateInstalled"),
        SchemaEntry(
            description="Date device was installed",
        ),
    ),
    (
        ("electrical", "solar", "*", "load"),
        SchemaEntry(
            description="State of load port on controller (if applicable)",
        ),
    ),
    (
        ("electrical", "solar", "*", "loadCurrent"),
        SchemaEntry(
            description=("Amperage being supplied to load directly connected to controller "),
            units="A",
        ),
    ),
    (
        ("electrical", "solar", "*", "location"),
        SchemaEntry(
            description="Installed location of device on vessel",
        ),
    ),
    (
        ("electrical", "solar", "*", "manufacturer", "URL"),
        SchemaEntry(
            description="Web referance / URL",
        ),
    ),
    (
        ("electrical", "solar", "*", "manufacturer", "model"),
        SchemaEntry(
            description="Model or part number",
        ),
    ),
    (
        ("electrical", "solar", "*", "manufacturer", "name"),
        SchemaEntry(
            description="Manufacturer's name",
        ),
    ),
    (
        ("electrical", "solar", "*", "name"),
        SchemaEntry(
            description=(
                "Unique ID of device (houseBattery, alternator, Generator, "
                "solar1, inverter, charger, combiner, etc.) "
            ),
        ),
    ),
    (
        ("electrical", "solar", "*", "panelCurrent"),
        SchemaEntry(
            description="Amperage being supplied from Solar Panels to controller",
            units="A",
        ),
    ),
    (
        ("electrical", "solar", "*", "panelPower"),
        SchemaEntry(
            description="Power being supplied from Solar Panels to controller",
            units="W",
        ),
    ),
    (
        ("electrical", "solar", "*", "panelTemperature"),
        SchemaEntry(
            description="Temperature of panels",
            units="K",
        ),
    ),
    (
        ("electrical", "solar", "*", "panelVoltage"),
        SchemaEntry(
            description="Voltage being supplied from Solar Panels to controller",
            units="V",
        ),
    ),
    (
        ("electrical", "solar", "*", "setpointCurrent"),
        SchemaEntry(
            description="Target current limit",
            units="A",
        ),
    ),
    (
        ("electrical", "solar", "*", "setpointVoltage"),
        SchemaEntry(
            description="Target regulation voltage",
            units="V",
        ),
    ),
    (
        ("electrical", "solar", "*", "temperature"),
        SchemaEntry(
            description="Temperature measured within or on the device",
            units="K",
        ),
    ),
    (
        ("electrical", "solar", "*", "temperature", "faultLower"),
        SchemaEntry(
            description=("Lower fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "solar", "*", "temperature", "faultUpper"),
        SchemaEntry(
            description=("Upper fault temperature limit - device may disable/disconnect "),
            units="K",
        ),
    ),
    (
        ("electrical", "solar", "*", "temperature", "warnLower"),
        SchemaEntry(
            description="Lower operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "solar", "*", "temperature", "warnUpper"),
        SchemaEntry(
            description="Upper operational temperature limit",
            units="K",
        ),
    ),
    (
        ("electrical", "solar", "*", "voltage"),
        SchemaEntry(
            description="Voltage measured at or as close as possible to the device",
            units="V",
        ),
    ),
    (
        ("electrical", "solar", "*", "voltage", "ripple"),
        SchemaEntry(
            description="DC Ripple voltage",
            units="V",
        ),
    ),
    (
        ("electrical", "solar", "*", "yieldToday"),
        SchemaEntry(
            description="Total energy generated by Solar Panels today",
            units="J",
        ),
    ),
    (
        ("environment", "inside", "*"),
        SchemaEntry(
            description=(
                "This regex pattern is used for validation of the identifier "
                "for the environmental zone, eg. engineRoom, mainCabin, "
                "refrigerator "
            ),
        ),
    ),
    (
        ("environment", "inside", "*", "airDensity"),
        SchemaEntry(
            description="Air density in zone",
            units="kg/m3",
        ),
    ),
    (
        ("environment", "inside", "*", "dewPoint"),
        SchemaEntry(
            description="DEPRECATED: use dewPointTemperature",
            units="K",
        ),
    ),
    (
        ("environment", "inside", "*", "dewPointTemperature"),
        SchemaEntry(
            description="Dewpoint in zone",
            units="K",
        ),
    ),
    (
        ("environment", "inside", "*", "heatIndexTemperature"),
        SchemaEntry(
            description="Current heat index temperature in zone",
            units="K",
        ),
    ),
    (
        ("environment", "inside", "*", "illuminance"),
        SchemaEntry(
            description="Illuminance in zone",
            units="Lux",
        ),
    ),
    (
        ("environment", "inside", "*", "pressure"),
        SchemaEntry(
            description="Pressure in zone",
            units="Pa",
        ),
    ),
    (
        ("environment", "inside", "*", "relativeHumidity"),
        SchemaEntry(
            description="Relative humidity in zone",
            units="ratio",
        ),
    ),
    (
        ("environment", "inside", "*", "temperature"),
        SchemaEntry(
            description="Temperature",
            units="K",
        ),
    ),
    (
        ("resources", "charts", "*"),
        SchemaEntry(
            description="A chart",
        ),
    ),
    (
        ("resources", "charts", "*", "bounds"),
        SchemaEntry(
            description=(
                "The bounds of the chart. An array containing the position of "
                "the upper left corner, and the lower right corner. Useful "
                "when the chart isn't inherently geo-referenced. "
            ),
        ),
    ),
    (
        ("resources", "charts", "*", "chartFormat"),
        SchemaEntry(
            description="The format of the chart",
        ),
    ),
    (
        ("resources", "charts", "*", "chartLayers"),
        SchemaEntry(
            description=("If the chart format is WMS, the layers enabled for the chart. "),
        ),
    ),
    (
        ("resources", "charts", "*", "chartUrl"),
        SchemaEntry(
            description="A url to the chart file's storage location",
        ),
    ),
    (
        ("resources", "charts", "*", "description"),
        SchemaEntry(
            description="A description of the chart",
        ),
    ),
    (
        ("resources", "charts", "*", "geohash"),
        SchemaEntry(
            description="Position related to chart. Alternative to region",
        ),
    ),
    (
        ("resources", "charts", "*", "identifier"),
        SchemaEntry(
            description="Chart number",
        ),
    ),
    (
        ("resources", "charts", "*", "name"),
        SchemaEntry(
            description="Chart common name",
        ),
    ),
    (
        ("resources", "charts", "*", "region"),
        SchemaEntry(
            description=(
                "Region related to note. A pointer to a region UUID. Alternative to geohash "
            ),
        ),
    ),
    (
        ("resources", "charts", "*", "scale"),
        SchemaEntry(
            description="The scale of the chart, the larger number from 1:200000",
        ),
    ),
    (
        ("resources", "charts", "*", "tilemapUrl"),
        SchemaEntry(
            description=("A url to the tilemap of the chart for use in TMS chartplotting apps "),
        ),
    ),
    (
        ("resources", "notes", "*"),
        SchemaEntry(
            description=(
                "A note about a region, named with a UUID. Notes might "
                "include navigation or cruising info, images, or anything "
            ),
        ),
    ),
    (
        ("resources", "notes", "*", "description"),
        SchemaEntry(
            description="A textual description of the note",
        ),
    ),
    (
        ("resources", "notes", "*", "geohash"),
        SchemaEntry(
            description="Position related to note. Alternative to region or position",
        ),
    ),
    (
        ("resources", "notes", "*", "mimeType"),
        SchemaEntry(
            description="MIME type of the note",
        ),
    ),
    (
        ("resources", "notes", "*", "position"),
        SchemaEntry(
            description="Position related to note. Alternative to region or geohash",
        ),
    ),
    (
        ("resources", "notes", "*", "region"),
        SchemaEntry(
            description=(
                "Region related to note. A pointer to a region UUID. "
                "Alternative to position or geohash "
            ),
        ),
    ),
    (
        ("resources", "notes", "*", "title"),
        SchemaEntry(
            description="Note's common name",
        ),
    ),
    (
        ("resources", "notes", "*", "url"),
        SchemaEntry(
            description="Location of the note",
        ),
    ),
    (
        ("resources", "regions", "*"),
        SchemaEntry(
            description="A region of interest, each named with a UUID",
        ),
    ),
    (
        ("resources", "regions", "*", "feature"),
        SchemaEntry(
            description=("A Geo JSON feature object which describes the regions boundary "),
        ),
    ),
    (
        ("resources", "regions", "*", "feature", "properties"),
        SchemaEntry(
            description="Additional data of any type",
        ),
    ),
    (
        ("resources", "regions", "*", "geohash"),
        SchemaEntry(
            description="geohash of the approximate boundary of this region",
        ),
    ),
    (
        ("resources", "routes", "*"),
        SchemaEntry(
            description="A route, named with a UUID",
        ),
    ),
    (
        ("resources", "routes", "*", "description"),
        SchemaEntry(
            description="A description of the route",
        ),
    ),
    (
        ("resources", "routes", "*", "distance"),
        SchemaEntry(
            description="Total distance from start to end",
            units="m",
        ),
    ),
    (
        ("resources", "routes", "*", "end"),
        SchemaEntry(
            description="The waypoint UUID at the end of the route",
        ),
    ),
    (
        ("resources", "routes", "*", "feature"),
        SchemaEntry(
            description=(
                "A Geo JSON feature object which describes the route between the waypoints "
            ),
        ),
    ),
    (
        ("resources", "routes", "*", "feature", "properties"),
        SchemaEntry(
            description="Additional data of any type",
        ),
    ),
    (
        ("resources", "routes", "*", "name"),
        SchemaEntry(
            description="Route's common name",
        ),
    ),
    (
        ("resources", "routes", "*", "start"),
        SchemaEntry(
            description="The waypoint UUID at the start of the route",
        ),
    ),
    (
        ("resources", "waypoints", "*"),
        SchemaEntry(
            description="A waypoint, named with a UUID",
        ),
    ),
    (
        ("sails", "inventory", "*"),
        SchemaEntry(
            description="'sail' data type.",
        ),
    ),
    (
        ("sails", "inventory", "*", "active"),
        SchemaEntry(
            description="Indicates wether this sail is currently in use or not",
        ),
    ),
    (
        ("sails", "inventory", "*", "area"),
        SchemaEntry(
            description="The total area of this sail in square meters",
            units="m2",
        ),
    ),
    (
        ("sails", "inventory", "*", "brand"),
        SchemaEntry(
            description="The brand of the sail (optional)",
        ),
    ),
    (
        ("sails", "inventory", "*", "material"),
        SchemaEntry(
            description="The material the sail is made from (optional)",
        ),
    ),
    (
        ("sails", "inventory", "*", "maximumWind"),
        SchemaEntry(
            description="The maximum wind speed this sail can be used with",
            units="m/s",
        ),
    ),
    (
        ("sails", "inventory", "*", "minimumWind"),
        SchemaEntry(
            description="The minimum wind speed this sail can be used with",
            units="m/s",
        ),
    ),
    (
        ("sails", "inventory", "*", "name"),
        SchemaEntry(
            description="An unique identifier by which the crew identifies a sail",
        ),
    ),
    (
        ("sails", "inventory", "*", "reducedState"),
        SchemaEntry(
            description="An object describing reduction of sail area",
        ),
    ),
    (
        ("sails", "inventory", "*", "reducedState", "furledRatio"),
        SchemaEntry(
            description=("Ratio of sail reduction, 0 means full and 1 is completely furled in "),
        ),
    ),
    (
        ("sails", "inventory", "*", "reducedState", "reduced"),
        SchemaEntry(
            description="describes whether the sail is reduced or not",
        ),
    ),
    (
        ("sails", "inventory", "*", "reducedState", "reefs"),
        SchemaEntry(
            description="Number of reefs set, 0 means full",
        ),
    ),
    (
        ("sails", "inventory", "*", "type"),
        SchemaEntry(
            description="The type of sail",
        ),
    ),
    (
        ("tanks", "baitWell", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "baitWell", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "baitWell", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "baitWell", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "baitWell", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "baitWell", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "baitWell", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "baitWell", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "baitWell", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "baitWell", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
    (
        ("tanks", "ballast", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "ballast", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "ballast", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "ballast", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "ballast", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "ballast", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "ballast", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "ballast", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "ballast", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "ballast", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
    (
        ("tanks", "blackWater", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "blackWater", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "blackWater", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "blackWater", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "blackWater", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "blackWater", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "blackWater", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "blackWater", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "blackWater", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "blackWater", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
    (
        ("tanks", "freshWater", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "freshWater", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "freshWater", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "freshWater", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "freshWater", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "freshWater", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "freshWater", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "freshWater", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "freshWater", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "freshWater", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
    (
        ("tanks", "fuel", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "fuel", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "fuel", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "fuel", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "fuel", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "fuel", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "fuel", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "fuel", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "fuel", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "fuel", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
    (
        ("tanks", "gas", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "gas", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "gas", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "gas", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "gas", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "gas", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "gas", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "gas", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "gas", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "gas", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
    (
        ("tanks", "liveWell", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "liveWell", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "liveWell", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "liveWell", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "liveWell", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "liveWell", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "liveWell", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "liveWell", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "liveWell", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "liveWell", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
    (
        ("tanks", "lubrication", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "lubrication", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "lubrication", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "lubrication", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "lubrication", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "lubrication", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "lubrication", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "lubrication", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "lubrication", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "lubrication", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
    (
        ("tanks", "wasteWater", "*"),
        SchemaEntry(
            description="Tank, one or many, within the vessel",
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "capacity"),
        SchemaEntry(
            description="Total capacity",
            units="m3",
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "currentLevel"),
        SchemaEntry(
            description="Level of fluid in tank 0-100%",
            units="ratio",
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "currentVolume"),
        SchemaEntry(
            description="Volume of fluid in tank",
            units="m3",
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "extinguishant"),
        SchemaEntry(
            description="The preferred extinguishant to douse a fire in this tank",
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "name"),
        SchemaEntry(
            description=(
                "The name of the tank. Useful if multiple tanks of a certain type are on board "
            ),
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "pressure"),
        SchemaEntry(
            description="Pressure of contents in tank, especially LPG/gas",
            units="Pa",
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "temperature"),
        SchemaEntry(
            description="Temperature of tank, especially cryogenic or LPG/gas",
            units="K",
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "type"),
        SchemaEntry(
            description="The type of tank",
        ),
    ),
    (
        ("tanks", "wasteWater", "*", "viscosity"),
        SchemaEntry(
            description="Viscosity of the fluid, if applicable",
            units="Pa/s",
        ),
    ),
]


def lookup_schema(path: str) -> SchemaEntry | None:
    entry = _EXACT_ENTRIES.get(path)
    if entry:
        return entry
    parts = tuple(path.split("."))
    for pattern, pattern_entry in _PATTERN_ENTRIES:
        if _match_pattern(pattern, parts):
            return pattern_entry
    return None


def _match_pattern(pattern: tuple[str, ...], path: tuple[str, ...]) -> bool:
    if len(pattern) != len(path):
        return False
    for expected, actual in zip(pattern, path):
        if expected == "*":
            continue
        if expected != actual:
            return False
    return True
