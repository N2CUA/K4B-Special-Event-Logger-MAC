import re


def normalize_park_reference(value, default_prefix="US", allow_blank=False):
    """Normalize a POTA Park Reference.

    Examples accepted: 2155 -> US-2155, US2155 -> US-2155,
    US-2155 -> US-2155, CA0008 -> CA-0008.
    """
    text = (value or "").strip().upper().replace(" ", "")
    if not text:
        if allow_blank:
            return ""
        raise ValueError("Enter a POTA Park Reference such as US-2155.")

    if text.isdigit():
        prefix = default_prefix.upper()
        digits = text
    else:
        match = re.fullmatch(r"([A-Z]{1,4})-?(\d+)", text)
        if not match:
            raise ValueError("Enter a POTA Park Reference such as US-2155.")
        prefix, digits = match.groups()

    if len(digits) < 4:
        raise ValueError("A POTA Park Reference uses a prefix, a dash, and four or more digits, such as US-2155.")
    return f"{prefix}-{digits}"


def normalize_us_park_reference(value, allow_blank=False):
    ref = normalize_park_reference(value, default_prefix="US", allow_blank=allow_blank)
    if not ref:
        return ref
    if not ref.startswith("US-"):
        raise ValueError("For this K4B activation, enter a U.S. POTA Park Reference such as US-2155.")
    return ref
