import re
from pathlib import Path

_FIELD_RE = re.compile(r"<([A-Za-z0-9_]+):(\d+)(?::[^>]*)?>", re.IGNORECASE)
_TOKEN_RE = re.compile(r"<(EOH|EOR)>", re.IGNORECASE)


def parse_adif_text(text):
    """Parse enough ADIF for K4B log interchange while respecting field lengths."""
    records = []
    current = {}
    pos = 0
    n = len(text)

    while pos < n:
        field_match = _FIELD_RE.search(text, pos)
        token_match = _TOKEN_RE.search(text, pos)

        next_match = None
        kind = None
        if field_match and token_match:
            if field_match.start() < token_match.start():
                next_match, kind = field_match, "field"
            else:
                next_match, kind = token_match, "token"
        elif field_match:
            next_match, kind = field_match, "field"
        elif token_match:
            next_match, kind = token_match, "token"
        else:
            break

        if kind == "token":
            token = next_match.group(1).upper()
            pos = next_match.end()
            if token == "EOR":
                if current:
                    records.append(current)
                    current = {}
            elif token == "EOH":
                current = {}
            continue

        name = next_match.group(1).upper()
        length = int(next_match.group(2))
        value_start = next_match.end()
        value_end = min(value_start + length, n)
        current[name] = text[value_start:value_end]
        pos = value_end

    if current:
        records.append(current)
    return records


def read_adif(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_adif_text(text)


def _date_to_iso(value):
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return ""


def _time_to_hhmm(value):
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    return digits[:4] if len(digits) >= 4 else ""


def _mode_from_adif(record):
    submode = (record.get("SUBMODE") or "").strip().upper()
    mode = (record.get("MODE") or "").strip().upper()
    if submode:
        return submode
    return mode


def record_to_qso(record):
    call = (record.get("CALL") or "").strip().upper()
    date_utc = _date_to_iso(record.get("QSO_DATE"))
    time_utc = _time_to_hhmm(record.get("TIME_ON"))
    band = (record.get("BAND") or "").strip().lower()
    mode = _mode_from_adif(record)
    if not call or not date_utc or not time_utc or not band or not mode:
        return None

    my_park = (record.get("MY_SIG_INFO") or "").strip().upper()
    their_park = (record.get("SIG_INFO") or "").strip().upper()
    my_sig = (record.get("MY_SIG") or "").strip().upper()
    pota_active = bool(my_park) and (not my_sig or my_sig == "POTA")
    return {
        "date_utc": date_utc,
        "time_utc": time_utc,
        "call": call,
        "band": band,
        "mode": mode,
        "frequency_mhz": (record.get("FREQ") or "").strip(),
        "rst_sent": (record.get("RST_SENT") or "").strip(),
        "rst_rcvd": (record.get("RST_RCVD") or "").strip(),
        "pota_active": pota_active,
        "my_park": my_park if pota_active else "",
        "their_park": their_park,
        "grid": (record.get("GRIDSQUARE") or "").strip(),
        "operator": (record.get("OPERATOR") or "").strip().upper(),
        "notes": (record.get("COMMENT") or "").strip(),
        "station_callsign": (record.get("STATION_CALLSIGN") or "").strip().upper(),
    }
