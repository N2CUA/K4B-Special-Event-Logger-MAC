from datetime import datetime, timezone
from pathlib import Path

ADIF_VERSION = "3.1.7"
PROGRAM_ID = "K4B_LOGGER"
PROGRAM_VERSION = "2.0.4"


def _field(name, value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return f"<{name}:{len(text)}>{text}"


def _adif_mode(mode):
    mode = (mode or "").strip().upper()
    mapping = {
        "FT8": ("MFSK", "FT8"), "FT4": ("MFSK", "FT4"), "JS8": ("MFSK", "JS8"),
        "PSK31": ("PSK", "PSK31"), "PSK63": ("PSK", "PSK63"), "JT65": ("JT65", ""),
        "JT9": ("JT9", ""), "Q65": ("MFSK", "Q65"), "RTTY": ("RTTY", ""),
    }
    return mapping.get(mode, (mode, ""))


def render_adif(setup, qsos):
    created = datetime.now(timezone.utc).strftime("%Y%m%d %H%M%S")
    header = "".join([
        _field("ADIF_VER", ADIF_VERSION), _field("PROGRAMID", PROGRAM_ID),
        _field("PROGRAMVERSION", PROGRAM_VERSION), _field("CREATED_TIMESTAMP", created), "<EOH>\n",
    ])
    station_call = setup.get("station_call", "K4B").upper()
    operator_default = setup.get("operator_call", "").upper()
    my_grid = setup.get("grid_square", "")
    setup_park = setup.get("my_park", "").upper() if setup.get("pota_enabled") else ""

    lines = [header]
    for qso in qsos:
        date = qso.get("date_utc", "").replace("-", "")
        mode, submode = _adif_mode(qso.get("mode", ""))
        qso_station_call = qso.get("station_callsign", "").upper() or station_call
        parts = [
            _field("CALL", qso.get("call", "").upper()), _field("QSO_DATE", date),
            _field("TIME_ON", qso.get("time_utc", "")), _field("BAND", qso.get("band", "").lower()),
            _field("MODE", mode),
        ]
        if submode:
            parts.append(_field("SUBMODE", submode))
        parts.extend([
            _field("FREQ", qso.get("frequency_mhz", "")), _field("RST_SENT", qso.get("rst_sent", "")),
            _field("RST_RCVD", qso.get("rst_rcvd", "")), _field("GRIDSQUARE", qso.get("grid", "")),
            _field("STATION_CALLSIGN", qso_station_call), _field("OPERATOR", qso.get("operator", "").upper() or operator_default),
            _field("MY_GRIDSQUARE", my_grid),
        ])

        # POTA status belongs to the individual QSO, not to whatever setup
        # happens to be active later when a mixed log is exported. Older K4B
        # records did not have pota_active, so a stored my_park is the legacy
        # signal that the contact was made from a POTA activation.
        pota_active = qso.get("pota_active")
        if pota_active is None:
            pota_active = bool(qso.get("my_park", "").strip())
        if pota_active:
            my_park = qso.get("my_park", "").upper() or setup_park
            if my_park:
                parts.extend([_field("MY_SIG", "POTA"), _field("MY_SIG_INFO", my_park)])
            their_park = qso.get("their_park", "").upper()
            if their_park:
                parts.extend([_field("SIG", "POTA"), _field("SIG_INFO", their_park)])

        parts.extend([_field("COMMENT", qso.get("notes", "")), "<EOR>\n"])
        lines.append("".join(parts))
    return "".join(lines)


def write_adif(path, setup, qsos):
    Path(path).write_text(render_adif(setup, qsos), encoding="utf-8")
