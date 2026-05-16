"""Tests for the layered Morse table registry and the file loader."""
import os
import pathlib

import pytest

from bip39_morse import morse


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_JP = REPO_ROOT / 'examples' / 'japanese.txt'
EXAMPLES_PL = REPO_ROOT / 'examples' / 'polish.txt'
EXAMPLES_EL = REPO_ROOT / 'examples' / 'greek.txt'


@pytest.fixture(autouse=True)
def _isolate_tables():
    """Each test starts with only built-in en+ru loaded; restore afterwards."""
    morse.reset_tables()
    yield
    morse.reset_tables()


def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body, encoding='utf-8')
    return str(p)


def test_default_locales_are_en_ru():
    assert morse.list_locales() == ['en', 'ru']
    assert morse.last_loaded_locale() == 'ru'


def test_load_japanese_example_file():
    locale = morse.load_table_file(str(EXAMPLES_JP))
    assert locale == 'jp'
    assert 'jp' in morse.list_locales()
    assert morse.last_loaded_locale() == 'jp'
    jp = morse.locale_table('jp')
    # A few canonical Wabun entries
    assert jp['イ'] == '.-'
    assert jp['ロ'] == '.-.-'
    assert jp['ン'] == '.-.-.'


def test_unknown_locale_raises():
    with pytest.raises(KeyError):
        morse.locale_table('xx')


def test_load_file_missing_header(tmp_path):
    path = _write(tmp_path, 't.txt', 'a .-\n')
    with pytest.raises(ValueError, match='missing.*locale'):
        morse.load_table_file(path)


def test_load_file_empty_mapping(tmp_path):
    path = _write(tmp_path, 't.txt', '# locale: zz\n')
    with pytest.raises(ValueError, match='no mapping entries'):
        morse.load_table_file(path)


def test_load_file_malformed_line(tmp_path):
    path = _write(tmp_path, 't.txt', '# locale: zz\njustoneword\n')
    with pytest.raises(ValueError, match='malformed'):
        morse.load_table_file(path)


def test_load_file_multichar(tmp_path):
    path = _write(tmp_path, 't.txt', '# locale: zz\nab .-\n')
    with pytest.raises(ValueError, match='single character'):
        morse.load_table_file(path)


def test_load_file_invalid_morse(tmp_path):
    path = _write(tmp_path, 't.txt', '# locale: zz\nx .-x\n')
    with pytest.raises(ValueError, match='morse code'):
        morse.load_table_file(path)


def test_later_file_overrides_builtin_for_same_char(tmp_path):
    """Loading a file that redefines 'a' must change char_to_bits('a')."""
    # Pre-override
    assert morse.char_to_bits('a') == '01'
    path = _write(tmp_path, 'override.txt', '# locale: en\na .---\n')
    morse.load_table_file(path)
    # Post-override: 'a' = .--- → 0111
    assert morse.char_to_bits('a') == '0111'


def test_later_file_locale_table_overrides(tmp_path):
    """Within a locale, later definitions override earlier ones."""
    path1 = _write(tmp_path, 'a.txt', '# locale: zz\nx .-\n')
    path2 = _write(tmp_path, 'b.txt', '# locale: zz\nx ---\n')
    morse.load_table_file(path1)
    morse.load_table_file(path2)
    assert morse.locale_table('zz')['x'] == '---'


def test_reverse_uses_loaded_locale():
    """Reverse decoding with locale='jp' must yield katakana, not Latin."""
    morse.load_table_file(str(EXAMPLES_JP))
    # 'イ' has code '.-' = bits '01'.
    out = morse.bits_to_text('01', locale='jp')
    assert out == 'イ'


def test_same_bits_decode_differently_per_locale():
    """Bits '01' is イ in jp, A in en, А in ru — locale picks the alphabet."""
    morse.load_table_file(str(EXAMPLES_JP))
    assert morse.bits_to_text('01', locale='en') == 'A'
    assert morse.bits_to_text('01', locale='ru') == 'А'
    assert morse.bits_to_text('01', locale='jp') == 'イ'


def test_forward_accepts_japanese_chars_after_load():
    """After loading jp, char_to_bits must accept katakana characters."""
    with pytest.raises(ValueError):
        morse.char_to_bits('イ')  # not loaded yet
    morse.load_table_file(str(EXAMPLES_JP))
    assert morse.char_to_bits('イ') == '01'
    assert morse.char_to_bits('ン') == '01010'


def test_reset_drops_user_layers():
    morse.load_table_file(str(EXAMPLES_JP))
    assert 'jp' in morse.list_locales()
    morse.reset_tables()
    assert morse.list_locales() == ['en', 'ru']
    with pytest.raises(KeyError):
        morse.locale_table('jp')


def test_last_loaded_locale_tracks_appends(tmp_path):
    assert morse.last_loaded_locale() == 'ru'
    morse.load_table_file(str(EXAMPLES_JP))
    assert morse.last_loaded_locale() == 'jp'
    # Loading an en-override file moves last-loaded back to en.
    path = _write(tmp_path, 'en2.txt', '# locale: en\na .-\n')
    morse.load_table_file(path)
    assert morse.last_loaded_locale() == 'en'


def test_bits_to_text_falls_through_to_punctuation(tmp_path):
    """A locale whose letter table has no short codes forces bits_to_text
    to fall through letters → digits → punctuation. Bits '001100' is `?`
    (punctuation, length 6); no letter matches and no 5-bit digit
    prefix '00110' is in the digit table."""
    path = _write(tmp_path, 'no_short.txt', '# locale: xx\nz -.--\n')
    morse.load_table_file(path)
    assert morse.bits_to_text('001100', locale='xx') == '?'


def test_bits_to_text_raises_when_nothing_matches(tmp_path):
    """If letter, digit, and punctuation tables all miss, bits_to_text
    must raise ValueError. Three bits cannot match any code (letters need
    at least 4 here, digits 5, punctuation 6)."""
    path = _write(tmp_path, 'no_short.txt', '# locale: xx\nz -.--\n')
    morse.load_table_file(path)
    with pytest.raises(ValueError, match='No Morse match'):
        morse.bits_to_text('001', locale='xx')


# --- examples/polish.txt --------------------------------------------------

def test_load_polish_example_file():
    """Loading polish.txt registers nine letters under the en layer."""
    locale = morse.load_table_file(str(EXAMPLES_PL))
    assert locale == 'en'
    en = morse.locale_table('en')
    # A few canonical Polish entries
    assert en['ą'] == '.-.-'
    assert en['ł'] == '.-..-'
    assert en['ś'] == '...-...'
    # Built-in A-Z still present in the merged en table
    assert en['a'] == '.-'
    assert en['z'] == '--..'


@pytest.mark.parametrize('ch,code,bits', [
    ('ą', '.-.-',    '0101'),
    ('ć', '-.-..',   '10100'),
    ('ę', '..-..',   '00100'),
    ('ł', '.-..-',   '01001'),
    ('ń', '--.--',   '11011'),
    ('ó', '---.',    '1110'),
    ('ś', '...-...', '0001000'),
    ('ź', '--..-.',  '110010'),
    ('ż', '--..-',   '11001'),
])
def test_polish_letter_codes_match_itu(ch, code, bits):
    """Every Polish character in polish.txt maps to the ITU-R M.1677-1
    code and char_to_bits produces the expected bit string."""
    morse.load_table_file(str(EXAMPLES_PL))
    assert morse.locale_table('en')[ch] == code
    assert morse.char_to_bits(ch) == bits
    assert morse.char_to_bits(ch.upper()) == bits  # case-insensitive


def test_polish_roundtrip_forward_reverse_forward():
    """Round-trip required by the issue DoD: a phrase whose entropy is
    derived from Polish characters must produce the same entropy hex when
    fed back through forward mode after reverse decoding."""
    morse.load_table_file(str(EXAMPLES_PL))
    phrase_in = 'ĄĆĘŁŃÓŚŹŻ' * 4  # 9 chars × 4 = 36 chars, 46×4=184 bits worth
    bits = ''.join(morse.char_to_bits(c) for c in phrase_in)
    assert len(bits) >= 128
    entropy = bits[:128]
    text = morse.bits_to_text(entropy, locale='en')
    re_bits = ''.join(morse.char_to_bits(c) for c in text)
    assert re_bits[:128] == entropy


def test_polish_shared_codes_match_other_locales():
    """Six of nine Polish letters share a bit-string with an existing
    extension (Ą≡Ä, Ć≡Ç, Ę≡É, Ł≡È, Ń≡Ñ, Ó≡Ö). Verify that the codes
    documented in polish.txt are consistent with the codes in
    german/french/spanish.txt."""
    morse.load_table_file(str(REPO_ROOT / 'examples' / 'german.txt'))
    morse.load_table_file(str(REPO_ROOT / 'examples' / 'french.txt'))
    morse.load_table_file(str(REPO_ROOT / 'examples' / 'spanish.txt'))
    morse.load_table_file(str(EXAMPLES_PL))
    en = morse.locale_table('en')
    pairs = [('ą', 'ä'), ('ć', 'ç'), ('ę', 'é'), ('ł', 'è'),
             ('ń', 'ñ'), ('ó', 'ö')]
    for pl, other in pairs:
        assert en[pl] == en[other], f'{pl!r} and {other!r} must share the same code'


def test_polish_layer_order_decides_reverse_winner(tmp_path):
    """When polish.txt is loaded BEFORE german.txt, bits 0101 must decode
    to Ą (Polish first); the reverse load order makes it Ä. This locks in
    the documented behaviour referenced in the polish.txt header comment."""
    # Polish first, then German.
    morse.load_table_file(str(EXAMPLES_PL))
    morse.load_table_file(str(REPO_ROOT / 'examples' / 'german.txt'))
    # 0101 alone — the algorithm picks longest letter at usage 0; both Ą
    # and Ä have length-4 code so it's purely an insertion-order tie-break.
    out_first_pl = morse.bits_to_text('0101', locale='en')
    assert out_first_pl == 'Ą'

    # Reset and reverse the load order.
    morse.reset_tables()
    morse.load_table_file(str(REPO_ROOT / 'examples' / 'german.txt'))
    morse.load_table_file(str(EXAMPLES_PL))
    out_first_de = morse.bits_to_text('0101', locale='en')
    assert out_first_de == 'Ä'


# --- examples/greek.txt ---------------------------------------------------

def test_load_greek_example_file():
    """Loading greek.txt registers a new locale 'el' with 24+1 letters."""
    locale = morse.load_table_file(str(EXAMPLES_EL))
    assert locale == 'el'
    assert 'el' in morse.list_locales()
    assert morse.last_loaded_locale() == 'el'
    el = morse.locale_table('el')
    # 24 ITU letters + final sigma
    assert len(el) == 25
    # A few canonical Greek entries
    assert el['α'] == '.-'
    assert el['ε'] == '.'
    assert el['τ'] == '-'
    assert el['ω'] == '.--'


@pytest.mark.parametrize('ch,code,bits', [
    ('α', '.-',    '01'),
    ('β', '-...',  '1000'),
    ('γ', '--.',   '110'),
    ('δ', '-..',   '100'),
    ('ε', '.',     '0'),
    ('ζ', '--..',  '1100'),
    ('η', '....',  '0000'),
    ('θ', '-.-.',  '1010'),
    ('ι', '..',    '00'),
    ('κ', '-.-',   '101'),
    ('λ', '.-..',  '0100'),
    ('μ', '--',    '11'),
    ('ν', '-.',    '10'),
    ('ξ', '-..-',  '1001'),
    ('ο', '---',   '111'),
    ('π', '.--.',  '0110'),
    ('ρ', '.-.',   '010'),
    ('σ', '...',   '000'),
    ('τ', '-',     '1'),
    ('υ', '-.--',  '1011'),
    ('φ', '..-.',  '0010'),
    ('χ', '----',  '1111'),
    ('ψ', '--.-',  '1101'),
    ('ω', '.--',   '011'),
])
def test_greek_letter_codes_match_itu(ch, code, bits):
    """Every ITU-R M.1677-1 Greek letter maps to the documented code and
    bit string, and lookup is case-insensitive via Python's str.lower
    (which handles Greek correctly)."""
    morse.load_table_file(str(EXAMPLES_EL))
    assert morse.locale_table('el')[ch] == code
    assert morse.char_to_bits(ch) == bits
    assert morse.char_to_bits(ch.upper()) == bits


def test_greek_one_bit_coverage():
    """Issue #6 DoD: verify both '0' and '1' resolve to a letter at
    length 1 in the el locale. Greek's Ε ('.') and Τ ('-') cover this,
    so reverse decoding has the same letter-only guarantee as en/ru."""
    morse.load_table_file(str(EXAMPLES_EL))
    assert morse.bits_to_text('0', locale='el') == 'Ε'
    assert morse.bits_to_text('1', locale='el') == 'Τ'


def test_greek_final_sigma_encodes_like_sigma():
    """ς and σ share the bit string '000'. In reverse direction σ wins
    (medial sigma listed first in greek.txt, so it's inserted into the
    bit-table first)."""
    morse.load_table_file(str(EXAMPLES_EL))
    assert morse.char_to_bits('σ') == '000'
    assert morse.char_to_bits('ς') == '000'
    # Reverse: '000' must decode to medial Σ (uppercase of σ), not final ς.
    assert morse.bits_to_text('000', locale='el') == 'Σ'


def test_greek_roundtrip_forward_reverse_forward():
    """Round-trip required by the issue DoD: a 128-bit entropy derived
    from a Greek phrase must survive forward → reverse → forward."""
    morse.load_table_file(str(EXAMPLES_EL))
    phrase = 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ' * 5  # 24 × 5 chars, well over 128 bits
    bits = ''.join(morse.char_to_bits(c) for c in phrase)
    assert len(bits) >= 128
    entropy = bits[:128]
    text = morse.bits_to_text(entropy, locale='el')
    re_bits = ''.join(morse.char_to_bits(c) for c in text)
    assert re_bits[:128] == entropy


def test_same_bits_decode_per_locale_el_extends_pattern():
    """Bits '01' is A in en, А in ru, イ in jp, Α in el — locale picks
    the alphabet. Extends the existing test_same_bits_decode_differently_per_locale."""
    morse.load_table_file(str(EXAMPLES_JP))
    morse.load_table_file(str(EXAMPLES_EL))
    assert morse.bits_to_text('01', locale='en') == 'A'
    assert morse.bits_to_text('01', locale='ru') == 'А'
    assert morse.bits_to_text('01', locale='jp') == 'イ'
    assert morse.bits_to_text('01', locale='el') == 'Α'


def test_greek_forward_accepts_chars_after_load():
    """Before loading greek.txt, char_to_bits('α') must error; after, it
    must produce the right bits. Mirrors test_forward_accepts_japanese_chars_after_load."""
    with pytest.raises(ValueError):
        morse.char_to_bits('α')
    morse.load_table_file(str(EXAMPLES_EL))
    assert morse.char_to_bits('α') == '01'
    assert morse.char_to_bits('Ω') == '011'
