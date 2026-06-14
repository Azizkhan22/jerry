from faster_whisper import WhisperModel

_model = None


def _get_model():
    global _model
    if _model is None:
        # "base" balances speed/accuracy on CPU. Use "small" or "medium"
        # for better accuracy if your machine can handle it.
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe_audio(audio_path: str) -> str:
    """Transcribe an audio file (e.g. a Telegram voice message .ogg) to text."""
    model = _get_model()
    segments, _ = model.transcribe(audio_path)
    return " ".join(segment.text.strip() for segment in segments).strip()
