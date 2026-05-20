import pytest
from bip39_morse.morse import char_to_bits, bits_to_text, LATIN, CYRILLIC, DIGITS, PUNCTUATION


LATIN_EXPECTED = {
    'a': '01', 'b': '1000', 'c': '1010', 'd': '100', 'e': '0',
    'f': '0010', 'g': '110', 'h': '0000', 'i': '00', 'j': '0111',
    'k': '101', 'l': '0100', 'm': '11', 'n': '10', 'o': '111',
    'p': '0110', 'q': '1101', 'r': '010', 's': '000', 't': '1',
    'u': '001', 'v': '0001', 'w': '011', 'x': '1001', 'y': '1011',
    'z': '1100',
}

CYRILLIC_EXPECTED = {
    'а': '01', 'б': '1000', 'в': '011', 'г': '110', 'д': '100',
    'е': '0', 'ж': '0001', 'з': '1100', 'и': '00', 'й': '0111',
    'к': '101', 'л': '0100', 'м': '11', 'н': '10', 'о': '111',
    'п': '0110', 'р': '010', 'с': '000', 'т': '1', 'у': '001',
    'ф': '0010', 'х': '0000', 'ц': '1010', 'ч': '1110', 'ш': '1111',
    'щ': '1101', 'ъ': '11011', 'ы': '1011', 'ь': '1001', 'э': '00100',
    'ю': '0011', 'я': '0101', 'ё': '0',
}

PUNCTUATION_EXPECTED = {
    # ITU-R M.1677-1 §1.1.3
    '.': '010101', ',': '110011', '-': '100001', '?': '001100', ':': '111000',
    # American Morse extensions (default-on in PUNCTUATION)
    '!': '101011', '_': '001101', '$': '0001001', '&': '01000', ';': '101010',
}


@pytest.mark.parametrize('ch,expected', LATIN_EXPECTED.items())
def test_latin(ch, expected):
    assert char_to_bits(ch) == expected


@pytest.mark.parametrize('ch,expected', LATIN_EXPECTED.items())
def test_latin_uppercase(ch, expected):
    assert char_to_bits(ch.upper()) == expected


@pytest.mark.parametrize('ch,expected', CYRILLIC_EXPECTED.items())
def test_cyrillic(ch, expected):
    assert char_to_bits(ch) == expected


@pytest.mark.parametrize('ch,expected', CYRILLIC_EXPECTED.items())
def test_cyrillic_uppercase(ch, expected):
    assert char_to_bits(ch.upper()) == expected


@pytest.mark.parametrize('ch,expected', PUNCTUATION_EXPECTED.items())
def test_punctuation(ch, expected):
    assert char_to_bits(ch) == expected


def test_yo_equals_ye():
    assert char_to_bits('ё') == char_to_bits('е')
    assert char_to_bits('Ё') == char_to_bits('Е')


def test_space_returns_empty():
    assert char_to_bits(' ') == ''


def test_all_26_latin():
    assert len(LATIN) == 26
    for ch in LATIN:
        bits = char_to_bits(ch)
        assert set(bits) <= {'0', '1'}
        assert len(bits) > 0


def test_all_33_cyrillic():
    # 32 + ё
    assert len(CYRILLIC) == 33
    for ch in CYRILLIC:
        bits = char_to_bits(ch)
        assert set(bits) <= {'0', '1'}
        assert len(bits) > 0


def test_unknown_char_raises():
    with pytest.raises(ValueError):
        char_to_bits('@')


DIGITS_EXPECTED = {
    '0': '11111', '1': '01111', '2': '00111', '3': '00011', '4': '00001',
    '5': '00000', '6': '10000', '7': '11000', '8': '11100', '9': '11110',
}


@pytest.mark.parametrize('ch,expected', DIGITS_EXPECTED.items())
def test_digits(ch, expected):
    assert char_to_bits(ch) == expected


def test_all_10_digits():
    assert len(DIGITS) == 10


def test_bits_to_text_letters_only():
    # Longest-prefix-match: 'p' = '.--.' = '0110' (4 bits), 'i' = '..' = '00' (2 bits).
    # The naïve split 'a'+'b' is not chosen because 'p' is longer.
    assert bits_to_text('011000') == 'PI'


def test_bits_to_text_single_bits():
    assert bits_to_text('0') == 'E'
    assert bits_to_text('1') == 'T'


def test_bits_to_text_prefers_letters_over_digits():
    # '00000' would match digit '5' but letters take precedence:
    # 'h' = '....' = '0000' (4 bits) + 'e' = '0' = 'HE'
    assert bits_to_text('00000') == 'HE'
    # '11111' would match digit '0'; longest letter prefix is 'o' = '---' = '111',
    # then remaining '11' = 'm' = '--' → 'OM'
    assert bits_to_text('11111') == 'OM'


def test_bits_to_text_prefers_letters_over_punctuation():
    # '010101' would match '.' = '.-.-.-' (punct, 6 bits); longest letter prefix
    # is 'r' = '.-.' = '010', then '101' = 'k' = '-.-' → 'RK'
    assert bits_to_text('010101') == 'RK'


def test_bits_to_text_letter_priority_uses_longest_letter():
    # '00100' = 'э' (Cyrillic letter, 5 bits) — full-length letter match
    assert bits_to_text('00100', locale='ru') == 'Э'


def test_bits_to_text_cyrillic():
    # Longest-prefix-match: 'п' = '.--.' = '0110' + 'и' = '..' = '00' → 'ПИ'.
    assert bits_to_text('011000', locale='ru') == 'ПИ'


def test_bits_to_text_roundtrip_letters():
    # 'привет' encoded then decoded should reproduce something whose
    # Morse bits start with the original
    src = 'привет'
    bits = ''.join(char_to_bits(c) for c in src)
    text = bits_to_text(bits, locale='ru')
    # Re-encode the produced text and compare bits prefix
    re_bits = ''.join(char_to_bits(c) for c in text)
    assert re_bits[:len(bits)] == bits


def test_bits_to_text_empty():
    assert bits_to_text('') == ''


def test_bits_to_text_spreads_across_letters():
    """Long runs of zeros should not collapse into a single repeated letter —
    the least-used rule rotates through H/S/I/E (all 0-only Latin codes)."""
    out = bits_to_text('0' * 32)
    # All H/S/I/E codes are all-zero, so output must consist only of those.
    assert set(out) <= {'H', 'S', 'I', 'E'}
    # And each must appear at least twice in a 32-bit run.
    for ch in 'HSIE':
        assert out.count(ch) >= 2, f'{ch!r} underused: {out!r}'


def test_bits_to_text_least_used_short_string():
    # Detailed trace for 8 zeros:
    #   pos 0: H/S/I/E all unused → longest H (4 bits)
    #   pos 4: S/I/E unused, H used → longest among unused = S (3 bits)
    #   pos 7: E unused, H,S used, I unused → wait remaining is 1 bit only
    #          so only E qualifies → pick E
    assert bits_to_text('0' * 8) == 'HSE'
