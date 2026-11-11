DOCUMENT_PREFIXES = frozenset({
    "ACC",
    "QTE",
    "SO",
    "SHP",
    "INV",
    "PAY",
    "DSP",
    "EXC",
})


def format_document_id(prefix: str, year: int, sequence: int) -> str:
    """Format an identifier according to the existing document ID convention."""
    normalized_prefix = prefix.strip().upper()
    if normalized_prefix not in DOCUMENT_PREFIXES:
        raise ValueError("Unsupported document ID prefix.")
    if not 1000 <= year <= 9999:
        raise ValueError("year must contain four digits.")
    if not 1 <= sequence <= 999999:
        raise ValueError("sequence must be between 1 and 999999.")
    return f"{normalized_prefix}-{year:04d}-{sequence:06d}"