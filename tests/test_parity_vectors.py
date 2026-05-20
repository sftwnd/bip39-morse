"""Self-consistency check for `tests/vectors/morse_parity_vectors.json`.

If `bip39_morse.morse.char_to_bits` changes behavior (e.g., new
PUNCTUATION entry, locale-specific override, fold semantics tweak) and
the parity-vectors JSON isn't regenerated, this test fails. Forces a
two-side update — regenerate the JSON via
`PYTHONPATH=. python tests/generate_morse_parity_vectors.py` and copy
to the iOS port's `MorseKeyTests/Vectors/`.
"""
import json
from pathlib import Path

import pytest

from bip39_morse import morse


VECTORS_PATH = Path(__file__).resolve().parent / 'vectors' / 'morse_parity_vectors.json'
EXAMPLES_DIR = Path(__file__).resolve().parent.parent / 'examples'


@pytest.fixture(autouse=True)
def _isolate_tables():
    """Reset+reload tables identically to the generator so the test
    runs against the same merged registry."""
    morse.reset_tables()
    for name in ('french.txt', 'german.txt', 'greek.txt', 'japanese.txt',
                 'polish.txt', 'spanish.txt'):
        morse.load_table_file(str(EXAMPLES_DIR / name))
    yield
    morse.reset_tables()


def _load_vectors() -> dict:
    with VECTORS_PATH.open() as f:
        return json.load(f)


def test_vectors_file_exists_and_nonempty():
    data = _load_vectors()
    assert data['version'] >= 1
    assert data['count'] == len(data['vectors'])
    assert data['count'] > 100, 'vectors file looks suspiciously small'


def test_each_vector_matches_current_char_to_bits():
    """For every vector, calling char_to_bits with the same args MUST
    produce the same expected_bits (or raise the same expected_error).
    If this fails — regenerate the JSON via
    `PYTHONPATH=. python tests/generate_morse_parity_vectors.py` and
    copy to the iOS port.
    """
    data = _load_vectors()
    mismatches: list[str] = []
    for v in data['vectors']:
        try:
            got = morse.char_to_bits(
                v['input'],
                locale=v.get('locale'),
                fold_diacritics=v.get('fold_diacritics', False),
            )
            if v.get('expected_error') is not None:
                mismatches.append(
                    f"input={v['input']!r}: expected error {v['expected_error']!r}, got {got!r}"
                )
            elif got != v['expected_bits']:
                mismatches.append(
                    f"input={v['input']!r} locale={v.get('locale')!r} fold={v.get('fold_diacritics')}: "
                    f"expected {v['expected_bits']!r}, got {got!r}"
                )
        except (ValueError, KeyError) as e:
            if v.get('expected_error') is None:
                mismatches.append(
                    f"input={v['input']!r}: expected {v['expected_bits']!r}, raised {type(e).__name__}"
                )
            elif type(e).__name__ != v['expected_error']:
                mismatches.append(
                    f"input={v['input']!r}: expected error {v['expected_error']!r}, got {type(e).__name__!r}"
                )

    assert not mismatches, (
        f'{len(mismatches)} of {data["count"]} vectors drifted from char_to_bits.\n'
        f'Regenerate: PYTHONPATH=. python tests/generate_morse_parity_vectors.py\n\n'
        + '\n'.join(mismatches[:20])
    )
