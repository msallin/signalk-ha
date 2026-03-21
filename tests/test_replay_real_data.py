import os
from pathlib import Path

from custom_components.signalk_ha.parser import parse_delta_text


def test_replay_signalk_messages_do_not_break() -> None:
    data_path = Path(__file__).parent / "testdata.json"
    limit_env = os.getenv("SIGNALK_TESTDATA_MAX_LINES", "")
    # Default to full replay; CI can cap via env var to keep the suite fast.
    max_lines = int(limit_env) if limit_env.isdigit() else None
    count = 0

    with data_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            count += 1
            result = parse_delta_text(text, ["vessels.self"])
            assert isinstance(result, dict), f"Line {line_number} should return dict"
            if max_lines is not None and count >= max_lines:
                break

    assert count > 0, "testdata.json should contain at least one message"
