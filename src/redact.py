import re

_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<EMAIL>"),
    (re.compile(r"(?:\+?91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b"), "<PHONE>"),
    (re.compile(r"\b\d{3}-\d{7}-\d{7}\b"), "<AMAZON_ORDER>"),
    (re.compile(r"\bOD\d{12,}\b", re.I), "<FLIPKART_ORDER>"),
    (re.compile(r"\b\d{12,19}\b"), "<LONG_NUMBER>"),
]


def redact(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text
