from langdetect import detect
from deep_translator import GoogleTranslator


def detect_language(text: str) -> str:
    try:
        return detect(text)
    except Exception:
        return "unknown"


def translate_to_spanish(text: str) -> str:
    try:
        return GoogleTranslator(source="auto", target="es").translate(text)
    except Exception:
        return text