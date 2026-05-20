"""Генератор conformance-векторов для проверки парности Python ↔ iOS
по encode-семантике Morse-таблиц.

Каждый vector — это `(input_char, locale, fold_diacritics) → expected_bits`.
JSON-файл результат сохраняется в `tests/vectors/morse_parity_vectors.json`
и должен использоваться идентично в обоих репо для cross-language
conformance-тестов.

Usage:
    python tests/generate_morse_parity_vectors.py
"""
import json
from pathlib import Path
from bip39_morse import morse


# Load all six example Morse tables that iOS also bundles, so the
# generated vectors cover the full Latin accent + Greek + Wabun set.
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / 'examples'
for name in ('french.txt', 'german.txt', 'greek.txt', 'japanese.txt',
             'polish.txt', 'spanish.txt'):
    morse.load_table_file(str(EXAMPLES_DIR / name))


def case(input_char: str, locale: str | None = None,
         fold_diacritics: bool = False, note: str = '') -> dict:
    """Build one vector. Returns dict with expected_bits or expected_error."""
    out = {'input': input_char, 'locale': locale,
           'fold_diacritics': fold_diacritics, 'note': note}
    try:
        out['expected_bits'] = morse.char_to_bits(
            input_char, locale=locale, fold_diacritics=fold_diacritics
        )
        out['expected_error'] = None
    except (ValueError, KeyError) as e:
        out['expected_bits'] = None
        out['expected_error'] = type(e).__name__
    return out


vectors = []

# --- English base alphabet (no locale → universal forward_table) ---
for ch in 'abcdefghijklmnopqrstuvwxyz':
    vectors.append(case(ch, note='en latin letter'))
    vectors.append(case(ch.upper(), note='en latin letter (uppercase)'))
for ch in '0123456789':
    vectors.append(case(ch, note='digit'))

# --- ITU-R punctuation (no locale → international) ---
for ch in '.,-?:':
    vectors.append(case(ch, note='ITU-R punctuation (no locale)'))

# --- American extensions (default-on in Python; iOS opt-in) ---
for ch in '!_$&;':
    vectors.append(case(ch, note='American extension (default-on)'))

# --- Russian Cyrillic letters (no locale, finds in forward_table) ---
for ch in 'абвгдежзийклмнопрстуфхцчшщъыьэюяё':
    vectors.append(case(ch, note='ru cyrillic letter (no locale)'))

# --- Soviet punctuation under ru locale ---
for ch in '.,':
    vectors.append(case(ch, locale='ru',
                        note='Soviet punctuation (locale=ru)'))

# --- Same punctuation, locale=en (falls back to PUNCTUATION) ---
for ch in '.,':
    vectors.append(case(ch, locale='en',
                        note='International punct (locale=en)'))

# --- French accents under fr locale (in Python all under 'en' layer) ---
for ch in 'àçéè':
    vectors.append(case(ch, note='French accent (no locale)'))
    vectors.append(case(ch.upper(), note='French accent (uppercase)'))

# --- German accents ---
for ch in 'äöüß':
    vectors.append(case(ch, note='German accent (no locale)'))

# --- Polish accents ---
for ch in 'ąćęłńóśźż':
    vectors.append(case(ch, note='Polish accent (no locale)'))

# --- Spanish accents ---
for ch in 'ñü':
    vectors.append(case(ch, note='Spanish accent (no locale)'))

# --- Greek (standalone locale) ---
for ch in 'αβγδεζηθικλμνξοπρστυφχψω':
    vectors.append(case(ch, locale='el', note='Greek (locale=el)'))

# --- Japanese Wabun (standalone locale) ---
for ch in 'イロハニホヘトチリヌ':
    vectors.append(case(ch, locale='jp', note='Japanese Wabun (locale=jp)'))

# --- fold_diacritics: diacritic with no direct Morse → fold to base ---
fold_cases = [
    ('é', 'fold é → e'),
    ('è', 'fold è → e'),
    ('š', 'fold š → s'),
    ('č', 'fold č → c'),
    ('ř', 'fold ř → r'),
    ('ñ', 'fold ñ → n'),
    ('á', 'fold á → a'),
    ('ÿ', 'fold ÿ → y'),
]
for ch, note in fold_cases:
    vectors.append(case(ch, fold_diacritics=True,
                        note=f'{note} (fold on)'))

# --- fold_diacritics: edge cases that should still raise ---
vectors.append(case('ß', fold_diacritics=True,
                    note='ß → ss (multi-char fold) → error'))
vectors.append(case('中', fold_diacritics=True,
                    note='CJK (non-Latin) → error'))

# --- Without fold: unknown chars raise ---
vectors.append(case('é', fold_diacritics=False,
                    note='unknown é without fold → error'))
vectors.append(case('🎉', fold_diacritics=False,
                    note='emoji → error'))

# Note: space (`' '`) is intentionally excluded — char_to_bits returns
# empty bits for it (word separator), but iOS handles space at the
# UI layer (ForwardScreen.handleTextChange) not via MorseRegistry.
# Including space in the vectors would require asymmetric handling.


out = {
    'version': 1,
    'description': (
        'Cross-language Morse encode parity vectors. Each vector: '
        'input character + optional locale + fold_diacritics flag. '
        'expected_bits is the bit string Python produces; iOS should '
        'produce identical output for the same input. expected_error '
        'is non-null when char_to_bits is expected to raise.'
    ),
    'generator': 'bip39-morse/tests/generate_morse_parity_vectors.py',
    'reset_tables': True,
    'preloaded_tables': [
        'french.txt', 'german.txt', 'greek.txt', 'japanese.txt',
        'polish.txt', 'spanish.txt',
    ],
    'count': len(vectors),
    'vectors': vectors,
}

OUTPUT = Path(__file__).resolve().parent / 'vectors' / 'morse_parity_vectors.json'
OUTPUT.parent.mkdir(exist_ok=True)
with OUTPUT.open('w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
    f.write('\n')

print(f'Generated {len(vectors)} vectors → {OUTPUT}')
