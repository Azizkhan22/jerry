def coerce_int(value, default: int) -> int:
    """Some models (notably llama-3.3 via Groq) occasionally emit numeric
    tool arguments as JSON strings, e.g. "5" instead of 5. Tool parameters
    that accept `int | str` use this to normalize either form back to int."""
    if isinstance(value, bool):  # bool is a subclass of int - exclude it
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default
