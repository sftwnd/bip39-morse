import re

LATIN = {
    'a': '.-',   'b': '-...', 'c': '-.-.', 'd': '-..', 'e': '.',
    'f': '..-.', 'g': '--.', 'h': '....', 'i': '..', 'j': '.---',
    'k': '-.-',  'l': '.-..', 'm': '--', 'n': '-.', 'o': '---',
    'p': '.--.', 'q': '--.-', 'r': '.-.', 's': '...', 't': '-',
    'u': '..-',  'v': '...-', 'w': '.--', 'x': '-..-', 'y': '-.--',
    'z': '--..',
}

CYRILLIC = {
    'а': '.-',   'б': '-...', 'в': '.--',  'г': '--.',  'д': '-..',
    'е': '.',    'ж': '...-', 'з': '--..',  'и': '..',   'й': '.---',
    'к': '-.-',  'л': '.-..', 'м': '--',   'н': '-.',   'о': '---',
    'п': '.--.', 'р': '.-.',  'с': '...',  'т': '-',    'у': '..-',
    'ф': '..-.', 'х': '....', 'ц': '-.-.',  'ч': '---.',  'ш': '----',
    'щ': '--.-', 'ъ': '--.--', 'ы': '-.--', 'ь': '-..-', 'э': '..-..',
    'ю': '..--', 'я': '.-.-', 'ё': '.',
}

DIGITS = {
    '0': '-----',
    '1': '.----',
    '2': '..---',
    '3': '...--',
    '4': '....-',
    '5': '.....',
    '6': '-....',
    '7': '--...',
    '8': '---..',
    '9': '----.',
}

PUNCTUATION = {
    # ITU-R M.1677-1 §1.1.3 — international standard.
    '.': '.-.-.-',
    ',': '--..--',
    '-': '-....-',
    '?': '..--..',
    ':': '---...',
    # American Morse extensions — non-ITU-R but widely used in American
    # radiotelegraph practice. Included by default; if you need strict
    # ITU-R behaviour, fork or wrap PUNCTUATION manually.
    #   `!`     — long-standing American convention (no ITU-R code).
    #   `_ $`   — American only, no ITU-R counterparts.
    #   `&`     — code `.-...` is the ITU-R "Wait" prosign; American
    #              usage re-binds it to the ampersand glyph.
    #   `;`     — `-.-.-.` is not defined in ITU-R; American convention.
    '!': '-.-.--',
    '_': '..--.-',
    '$': '...-..-',
    '&': '.-...',
    ';': '-.-.-.',
}


# Layered registry of letter alphabets.
# Each layer is (locale, {char_lowercase: morse_string}). Order is load order:
# built-in layers first, then any user-loaded files appended. When two layers
# define the same character, later layers win. Reverse decoding builds a
# per-locale view by merging only the layers tagged with that locale.
_LAYERS: list[tuple[str, dict[str, str]]] = [
    ('en', dict(LATIN)),
    ('ru', dict(CYRILLIC)),
]

_FORWARD_CACHE: dict[str, str] | None = None


def _invalidate_cache() -> None:
    global _FORWARD_CACHE
    _FORWARD_CACHE = None


def reset_tables() -> None:
    """Drop all user-loaded layers and restore the built-in en/ru pair."""
    global _LAYERS
    _LAYERS = [('en', dict(LATIN)), ('ru', dict(CYRILLIC))]
    _invalidate_cache()


def list_locales() -> list[str]:
    """Locales currently registered, in load order, deduplicated by first occurrence."""
    seen: set[str] = set()
    result: list[str] = []
    for loc, _ in _LAYERS:
        if loc not in seen:
            seen.add(loc)
            result.append(loc)
    return result


def last_loaded_locale() -> str:
    """Locale of the most recently appended layer (built-ins count too)."""
    return _LAYERS[-1][0]


def forward_table() -> dict[str, str]:
    """Merged character→morse map across all layers. Later layers override earlier."""
    global _FORWARD_CACHE
    if _FORWARD_CACHE is None:
        merged: dict[str, str] = {}
        for _, table in _LAYERS:
            for ch, morse in table.items():
                merged[ch.lower()] = morse
        _FORWARD_CACHE = merged
    return _FORWARD_CACHE


def locale_table(locale: str) -> dict[str, str]:
    """Merged character→morse map for one locale.

    Walks all layers in load order, keeping only those tagged with `locale`;
    later layers with the same character override earlier ones. Raises
    KeyError if the locale was never registered.
    """
    merged: dict[str, str] = {}
    found = False
    for loc, table in _LAYERS:
        if loc == locale:
            found = True
            for ch, morse in table.items():
                merged[ch.lower()] = morse
    if not found:
        raise KeyError(f'Unknown locale: {locale!r}')
    return merged


_LOCALE_HEADER = re.compile(r'#\s*locale\s*:\s*(\S+)\s*$', re.IGNORECASE)


def load_table_file(path: str) -> str:
    """Parse a Morse table file, append it as a new layer, return its locale.

    File format (UTF-8):
      - Header line `# locale: <code>` is required.
      - Lines starting with `#` are comments; blank lines ignored.
      - Data lines: `<char><whitespace><morse>` where morse uses `.` and `-`.
      - Letters are stored lowercase; lookup is case-insensitive.
    """
    locale: str | None = None
    mapping: dict[str, str] = {}
    with open(path, encoding='utf-8') as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith('#'):
                m = _LOCALE_HEADER.match(line)
                if m:
                    locale = m.group(1).lower()
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                raise ValueError(f'{path}:{lineno}: malformed entry: {raw.rstrip()!r}')
            ch, morse = parts
            if len(ch) != 1:
                raise ValueError(
                    f'{path}:{lineno}: expected single character, got {ch!r}'
                )
            if not morse or set(morse) - {'.', '-'}:
                raise ValueError(
                    f'{path}:{lineno}: morse code must contain only "." and "-", got {morse!r}'
                )
            mapping[ch.lower()] = morse
    if locale is None:
        raise ValueError(f'{path}: missing "# locale: <code>" header')
    if not mapping:
        raise ValueError(f'{path}: no mapping entries found')
    _LAYERS.append((locale, mapping))
    _invalidate_cache()
    return locale


def _to_bits(morse: str) -> str:
    return morse.replace('.', '0').replace('-', '1')


def char_to_bits(ch: str) -> str:
    """Convert a single character to a morse bit string ('.' → '0', '-' → '1').
    Returns empty string for space (word separator)."""
    if ch == ' ':
        return ''
    lower = ch.lower()
    morse = (
        forward_table().get(lower)
        or DIGITS.get(ch)
        or PUNCTUATION.get(ch)
    )
    if morse is None:
        raise ValueError(f'Unknown character: {ch!r}')
    return _to_bits(morse)


def _bits_table(alphabet: dict) -> dict:
    """Reverse map: bit-string → char. First-added char wins on collision."""
    result: dict = {}
    for ch, morse in alphabet.items():
        b = _to_bits(morse)
        if b not in result:
            result[b] = ch
    return result


def _upper_for_display(ch: str) -> str:
    """Uppercase a single character for reverse-mode display, preserving
    bit-length symmetry. Python's ``str.upper()`` maps a few lowercase
    letters to multi-character strings — notably German ``ß`` → ``'SS'``
    — which silently breaks the forward/reverse round-trip because
    ``'SS'`` has different bits than ``ß`` (and so the round-trip
    self-check the README tells users to perform would fail for any
    passphrase containing ``ß``). For ``ß`` we use ``ẞ`` (U+1E9E LATIN
    CAPITAL LETTER SHARP S) explicitly; all other characters fall
    through to ordinary ``str.upper()``."""
    if ch == 'ß':
        return 'ẞ'
    return ch.upper()


def _pick_least_used(
    bits: str,
    i: int,
    table: dict,
    max_len: int,
    usage: dict,
) -> tuple[str | None, int]:
    """Find the best matching code in `table` for bits[i:].
    Among all candidates (any length 1..max_len) prefer the one used the
    fewest times so far; break ties by preferring the longest code, then
    alphabetically (stable, deterministic).
    Returns (char, length_consumed) or (None, 0)."""
    candidates: list[tuple[int, int, str, int]] = []
    limit = min(max_len, len(bits) - i)
    for L in range(1, limit + 1):
        prefix = bits[i:i + L]
        if prefix in table:
            ch = _upper_for_display(table[prefix])
            # Sort key: (usage, -length, char). Smallest wins.
            candidates.append((usage.get(ch, 0), -L, ch, L))
    if not candidates:
        return None, 0
    candidates.sort()
    _, _, ch, L = candidates[0]
    return ch, L


def bits_to_text(bits: str, locale: str = 'en') -> str:
    """Decode a bit string into a printable text using the Morse alphabet of `locale`.

    Selection rule per position:
      1. Among letter codes that match a prefix at any length, choose the
         one used the fewest times so far (tie-break: longest, then
         alphabetical). This spreads the output across letters instead of
         collapsing into long runs of a single letter.
      2. If no letter matches at any length, fall back to digits (same
         least-used rule).
      3. If no digit, fall back to punctuation.

    For the built-in en/ru locales `e`/`е` cover '.' and `t`/`т` cover '-',
    so the letter table always matches at length 1 and no dead end can
    occur. Custom locales may not have this property; the digit and
    punctuation fallbacks exist for robustness in that case.
    """
    letters = locale_table(locale)
    letter_bits = _bits_table(letters)
    digit_bits = _bits_table(DIGITS)
    punct_bits = _bits_table(PUNCTUATION)

    # Largest letter code in the chosen locale, bounded below by punctuation length.
    max_code_len = max(
        (len(m) for m in letters.values()),
        default=1,
    )
    max_code_len = max(max_code_len, 6)
    usage: dict[str, int] = {}
    result: list[str] = []
    i = 0
    n = len(bits)
    while i < n:
        ch, used = _pick_least_used(bits, i, letter_bits, max_code_len, usage)
        if ch is None:
            ch, used = _pick_least_used(bits, i, digit_bits, max_code_len, usage)
        if ch is None:
            ch, used = _pick_least_used(bits, i, punct_bits, max_code_len, usage)
        if ch is None:
            raise ValueError(f'No Morse match at position {i}: {bits[i:]!r}')
        result.append(ch)
        usage[ch] = usage.get(ch, 0) + 1
        i += used
    return ''.join(result)
