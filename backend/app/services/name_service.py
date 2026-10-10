"""
name_module.py - Arabic -> English name transliteration + name matching.
Pure Python, no dependencies.

  to_english(name)        -> English version of an Arabic (or mixed) name
  names_match(a, b)       -> (is_match, score) comparing by consonant skeleton
"""
import re
import unicodedata
from difflib import SequenceMatcher

# ---------------------------------------------------------------- lexicon
# Generic corporate words are TRANSLATED (not transliterated).
CORPORATE = {
    "شركة": "Co.", "شركه": "Co.", "مؤسسة": "Establishment", "موسسه": "Establishment",
    "مؤسسه": "Establishment", "مجموعة": "Group", "مجموعه": "Group",
    "التجارة": "Trading", "تجارة": "Trading", "تجاره": "Trading", "التجاره": "Trading",
    "للتجارة": "Trading", "للتجاره": "Trading",
    "المحدودة": "Ltd.", "محدودة": "Ltd.", "المحدوده": "Ltd.",
    "ذ.م.م": "LLC", "للمقاولات": "Contracting", "المقاولات": "Contracting",
    "الصناعة": "Industries", "للصناعة": "Industries", "للصناعات": "Industries",
    "الصناعات": "Industries", "الاستثمار": "Investment", "للاستثمار": "Investment",
    "العقارية": "Real Estate", "للعقارات": "Real Estate", "الخدمات": "Services",
    "للخدمات": "Services", "التقنية": "Technology", "للتقنية": "Technology",
    "البنك": "Bank", "بنك": "Bank", "مصرف": "Bank", "المصرف": "Bank",
    "الدولية": "International", "العالمية": "Global", "للنقل": "Transport",
    "الغذائية": "Foods", "للأغذية": "Foods", "للاغذية": "Foods",
}

# Common personal names with a standard English spelling.
NAMES = {
    "محمد": "Mohammed", "احمد": "Ahmed", "أحمد": "Ahmed", "علي": "Ali", "عمر": "Omar",
    "عثمان": "Othman", "حسن": "Hassan", "حسين": "Hussein", "خالد": "Khalid",
    "يوسف": "Youssef", "ابراهيم": "Ibrahim", "إبراهيم": "Ibrahim", "اسماعيل": "Ismail",
    "فاطمة": "Fatima", "فاطمه": "Fatima", "عائشة": "Aisha", "مريم": "Maryam",
    "سعيد": "Said", "سالم": "Salem", "ناصر": "Nasser", "فهد": "Fahad",
    "عبدالله": "Abdullah", "عبد": "Abdul", "الله": "Allah", "الرحمن": "Rahman",
    "عبدالرحمن": "Abdulrahman", "عبدالعزيز": "Abdulaziz", "ابن": "Bin", "بن": "Bin",
    "ابو": "Abu", "أبو": "Abu", "الامل": "Al-Amal", "الأمل": "Al-Amal",
    "النور": "Al-Noor", "الفجر": "Al-Fajr", "الصباح": "Al-Sabah",
}

# ---------------------------------------------------------------- helpers
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")  # harakat + tatweel
_ARABIC = re.compile(r"[\u0600-\u06FF]")

def _norm_ar(w: str) -> str:
    w = _DIACRITICS.sub("", w)
    for a in "أإآٱ":
        w = w.replace(a, "ا")
    return w.replace("ى", "ي")

def is_arabic(s: str) -> bool:
    return bool(_ARABIC.search(s))

_CONS = {
    "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh", "د": "d",
    "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s", "ض": "d",
    "ط": "t", "ظ": "z", "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l",
    "م": "m", "ن": "n", "ه": "h", "پ": "p", "چ": "ch", "گ": "g", "ڤ": "v",
}

def _translit_word(w: str) -> str:
    """Rule-based sound->letters. Inserts 'a' between consonants (no harakat)."""
    w = _norm_ar(w)
    prefix = ""
    if w.startswith("ال") and len(w) > 3:
        prefix, w = "Al-", w[2:]
    out, last_vowel = [], True          # last_vowel: was the previous piece a vowel?
    n = len(w)

    def add_cons(c):
        nonlocal last_vowel
        if not last_vowel and out:      # consonant + consonant -> insert 'a'
            out.append("a")
        out.append(c)
        last_vowel = False

    def add_vowel(v):
        nonlocal last_vowel
        if last_vowel and out and out[-1].lower() == v:
            return
        out.append(v)
        last_vowel = True

    for i, ch in enumerate(w):
        nxt = w[i + 1] if i + 1 < n else ""
        if ch in ("ا", "ع"):
            add_vowel("A" if i == 0 else "a")
        elif ch == "ء" or ch == "ئ" or ch == "ؤ":
            add_vowel("a")
        elif ch == "و":
            if i == 0 or (nxt and nxt in "اىي"):
                add_cons("w")
            else:
                add_vowel("u")
        elif ch == "ي":
            if i == 0 or (nxt and nxt in "او"):
                add_cons("y")
            else:
                add_vowel("i")
        elif ch in ("ة",):
            add_vowel("a")
        elif ch in _CONS:
            add_cons(_CONS[ch])
        # anything else (digits, punctuation) ignored here
    word = "".join(out)
    word = word[:1].upper() + word[1:]
    if prefix:
        word = prefix + word[:1].upper() + word[1:]
    return word

def _translit_token(tok: str) -> str:
    n = _norm_ar(tok)
    for table in (CORPORATE, NAMES):
        for k, v in table.items():
            if n == _norm_ar(k):
                return v
    # prefix "لل" = ل + ال  (e.g. للتجارة)
    if n.startswith("لل"):
        alt = "ال" + n[2:]
        for k, v in CORPORATE.items():
            if _norm_ar(k) == alt:
                return v
    # "عبد" compounds: عبدالله handled above; عبد + X -> Abdul-X
    if n.startswith("عبد") and len(n) > 4:
        return "Abdul" + _translit_word(n[3:]).lower()
    return _translit_word(tok)

def to_english(name: str) -> str:
    """Arabic (or mixed) name -> English. Latin tokens pass through unchanged."""
    if not name or not is_arabic(name):
        return (name or "").strip()
    toks = re.split(r"\s+", name.strip())
    out = [_translit_token(t) if is_arabic(t) else t for t in toks]
    # English puts the legal suffix last: "شركة X للتجارة" -> "X Trading Co."
    suffixes = {"Co.", "Establishment", "Ltd.", "LLC"}
    head = [t for t in out if t not in suffixes]
    tail = [t for t in out if t in suffixes]
    return " ".join(head + tail)

# ---------------------------------------------------------------- matching
_GENERIC = {
    "co", "company", "ltd", "limited", "llc", "inc", "group", "trading", "establishment",
    "est", "corp", "corporation", "contracting", "industries", "investment", "services",
    "real", "estate", "technology", "bank", "international", "global", "transport", "foods",
    "the", "al", "el", "bin", "ibn", "abu",
}

def skeleton(token: str) -> str:
    """Consonant skeleton of a Latin token: 'Amal' -> 'ml', 'Mohammed' -> 'mhmd'."""
    t = unicodedata.normalize("NFKD", token.lower())
    t = re.sub(r"[^a-z]", "", t)
    for a, b in (("kh", "x"), ("sh", "s"), ("th", "t"), ("dh", "d"), ("gh", "g"),
                 ("ph", "f"), ("ch", "s"), ("ck", "k")):
        t = t.replace(a, b)
    t = t.translate(str.maketrans({"q": "k", "c": "k", "z": "s", "v": "f", "p": "b", "g": "g"}))
    t = re.sub(r"[aeiouyw]", "", t)       # drop vowels / semi-vowels
    t = re.sub(r"(.)\1+", r"\1", t)       # collapse doubles
    return t

def _core_tokens(name: str):
    eng = to_english(name) if is_arabic(name) else name
    eng = eng.replace("-", " ").replace(".", " ")
    toks = [t for t in re.split(r"\s+", eng) if t]
    core = [t for t in toks if t.lower() not in _GENERIC]
    return core or toks   # if everything was generic, fall back to all tokens

def names_match(a: str, b: str, threshold: float = 0.85):
    """Compare two names (Arabic or English) by consonant skeleton. Returns (bool, score)."""
    sa = " ".join(filter(None, (skeleton(t) for t in _core_tokens(a))))
    sb = " ".join(filter(None, (skeleton(t) for t in _core_tokens(b))))
    if not sa or not sb:
        return False, 0.0
    score = SequenceMatcher(None, sa, sb).ratio()
    return score >= threshold, round(score, 3)

# ---------------------------------------------------------------- tests
if __name__ == "__main__":
    cases = [
        ("شركة الأمل للتجارة", "Al-Amal Trading Co."),
        ("محمد أحمد", "Mohammed Ahmed"),
        ("محمد أحمد", "Muhammad Ahmad"),
        ("عبدالله خالد", "Abdullah Khaled"),
        ("الأمل", "Amal"),
        ("شركة الأمل للتجارة", "The Hope Trading Company"),   # translation trap -> must NOT match
        ("محمد أحمد", "Fatima Hassan"),                       # different person -> must NOT match
    ]
    for ar, en in cases:
        print(f"{ar!r:28} -> {to_english(ar)!r:28} vs {en!r:28} {names_match(ar, en)}")