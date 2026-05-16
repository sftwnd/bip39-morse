"""Property-based round-trip tests for bits_to_text ↔ char_to_bits.

Invariant: for any bit string of length 128 / 192 / 256 (the three BIP39
entropy sizes), feeding it through ``bits_to_text`` and re-encoding each
output character via ``char_to_bits`` must reproduce **exactly the same
bit string**. This is the property that makes the tool round-trippable
and is the precondition for the README's "round-trip self-check"
workflow that users are told to perform before trusting any real
mnemonic.

The invariant holds for every locale whose letter table covers the
1-bit codes ``0`` and ``1``: the built-in ``en`` and ``ru`` (``e``/``т``
cover ``0``/``1`` in their respective alphabets), the shipped Greek
``el`` (``Ε``/``Τ``), and any layered extension over ``en`` (since
``e``/``t`` remain part of the merged letter table). Wabun-style
locales (e.g. ``jp``) deliberately lack 1-bit codes and therefore
**cannot** satisfy this invariant for arbitrary inputs — they're
excluded from this file by design, not by oversight.

Hypothesis settings: ``derandomize=True`` makes each test fully
deterministic — the PRNG seed is derived from the function name, so CI
runs replay the same examples every time. For exploratory fuzzing
locally, override with ``--hypothesis-seed=random`` on the pytest
command line.
"""
import pathlib

import pytest
from hypothesis import given, settings, strategies as st

from bip39_morse import morse


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES = REPO_ROOT / 'examples'

ENTROPY_SIZES = [128, 192, 256]


@pytest.fixture(autouse=True)
def _isolate_tables():
    """Reset the layered Morse registry around every test so extensions
    loaded by one test don't leak into the next."""
    morse.reset_tables()
    yield
    morse.reset_tables()


def _bits_of_length(n: int) -> st.SearchStrategy[str]:
    """Hypothesis strategy: a string of exactly ``n`` chars from {'0','1'}."""
    return st.text(alphabet='01', min_size=n, max_size=n)


def _assert_roundtrip(bits: str, locale: str) -> None:
    text = morse.bits_to_text(bits, locale=locale)
    re_bits = ''.join(morse.char_to_bits(c) for c in text)
    assert re_bits == bits, (
        f'round-trip mismatch in locale={locale!r}:\n'
        f'  input bits  : {bits}\n'
        f'  text        : {text!r}\n'
        f'  re-encoded  : {re_bits}'
    )


# --- Built-in locales -----------------------------------------------------

@pytest.mark.parametrize('size', ENTROPY_SIZES)
@settings(derandomize=True, max_examples=100, deadline=None)
@given(data=st.data())
def test_roundtrip_builtin_en(data, size):
    bits = data.draw(_bits_of_length(size))
    _assert_roundtrip(bits, locale='en')


@pytest.mark.parametrize('size', ENTROPY_SIZES)
@settings(derandomize=True, max_examples=100, deadline=None)
@given(data=st.data())
def test_roundtrip_builtin_ru(data, size):
    bits = data.draw(_bits_of_length(size))
    _assert_roundtrip(bits, locale='ru')


# --- Shipped Greek (new alphabet, separate locale) ------------------------

@pytest.mark.parametrize('size', ENTROPY_SIZES)
@settings(derandomize=True, max_examples=100, deadline=None)
@given(data=st.data())
def test_roundtrip_greek_el(data, size):
    morse.load_table_file(str(EXAMPLES / 'greek.txt'))
    bits = data.draw(_bits_of_length(size))
    _assert_roundtrip(bits, locale='el')


# --- Latin accent extensions (layered over en) ----------------------------

@pytest.mark.parametrize('extension', [
    'german.txt', 'french.txt', 'spanish.txt', 'polish.txt',
])
@pytest.mark.parametrize('size', ENTROPY_SIZES)
@settings(derandomize=True, max_examples=50, deadline=None)
@given(data=st.data())
def test_roundtrip_en_with_extension(data, extension, size):
    """With an accent extension loaded, locale='en' still round-trips —
    the merged en-letter table still contains e/t for 1-bit coverage and
    the new accented chars only add longer codes."""
    morse.load_table_file(str(EXAMPLES / extension))
    bits = data.draw(_bits_of_length(size))
    _assert_roundtrip(bits, locale='en')


# --- Stacked: all four Latin accent extensions loaded together ------------

@pytest.mark.parametrize('size', ENTROPY_SIZES)
@settings(derandomize=True, max_examples=50, deadline=None)
@given(data=st.data())
def test_roundtrip_en_with_all_latin_extensions(data, size):
    """Worst case for letter-table density: all four ITU Latin accent
    extensions loaded. Round-trip must still hold."""
    for fname in ('german.txt', 'french.txt', 'spanish.txt', 'polish.txt'):
        morse.load_table_file(str(EXAMPLES / fname))
    bits = data.draw(_bits_of_length(size))
    _assert_roundtrip(bits, locale='en')
