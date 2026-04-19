import re
import unicodedata


CRU_MAP = {
    "premier cru": "1er cru",
    "1 er cru": "1er cru",
    "st ": "saint ",
    "st": "saint",
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("’", "'")
    text = re.sub(r"(?<=\w)'(?=\w)", "", text)
    text = re.sub(r"[-_/]+", " ", text)
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\bpremier cru\b", CRU_MAP["premier cru"], text)
    text = re.sub(r"\b1 er cru\b", CRU_MAP["1 er cru"], text)
    text = re.sub(r"\bst\b", CRU_MAP["st"], text)
    text = re.sub(r"[']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text
