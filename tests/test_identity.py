from custom_components.signalk_ha.identity import build_instance_id, resolve_vessel_identity


def test_resolve_vessel_identity_uses_mmsi() -> None:
    vessel = {"name": "ONA", "mmsi": "261006533"}
    identity = resolve_vessel_identity(vessel, "http://sk.local:3000/signalk/v1/api/")
    assert identity.vessel_id == "mmsi:261006533"
    assert identity.vessel_name == "ONA"


def test_resolve_vessel_identity_fallback_hash() -> None:
    vessel = {"name": "ONA"}
    identity = resolve_vessel_identity(vessel, "http://sk.local:3000/signalk/v1/api/")
    assert identity.vessel_id.startswith("hash:")


def test_resolve_vessel_identity_uses_alt_id() -> None:
    vessel = {"name": "ONA", "urn": "urn:mrn:imo:mmsi:123456789"}
    identity = resolve_vessel_identity(vessel, "http://sk.local:3000/signalk/v1/api/")
    assert identity.vessel_id == "urn:mrn:imo:mmsi:123456789"


def test_build_instance_id_is_stable() -> None:
    instance_a = build_instance_id("http://sk.local:3000/signalk/v1/api/", "mmsi:1")
    instance_b = build_instance_id("http://sk.local:3000/signalk/v1/api/", "mmsi:1")
    assert instance_a == instance_b
