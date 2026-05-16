"""Tests for the layered Morse table registry and the file loader."""
import os
import pathlib

import pytest

from bip39_morse import morse


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_JP = REPO_ROOT / 'examples' / 'japanese.txt'


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
