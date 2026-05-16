import json
import tempfile
from pathlib import Path
import pytest
from bip39_morse.bip39 import load_wordlist, entropy_to_mnemonic, indices_to_mnemonic

VECTORS_PATH = Path(__file__).parent / 'vectors' / 'trezor_vectors.json'


@pytest.fixture(scope='module')
def english_wordlist():
    return load_wordlist('english')


@pytest.fixture(scope='module')
def trezor_vectors():
    with open(VECTORS_PATH, encoding='utf-8') as f:
        data = json.load(f)
    return data['english']


def test_load_english():
    words = load_wordlist('english')
    assert len(words) == 2048
    assert words[0] == 'abandon'
    assert words[-1] == 'zoo'


def test_load_russian():
    words = load_wordlist('russian')
    assert len(words) == 2048


def test_load_custom_valid(tmp_path):
    custom = tmp_path / 'custom.txt'
    custom.write_text('\n'.join(f'word{i}' for i in range(2048)))
    words = load_wordlist(str(custom))
    assert len(words) == 2048
    assert words[0] == 'word0'


def test_load_custom_wrong_count(tmp_path):
    bad = tmp_path / 'bad.txt'
    bad.write_text('\n'.join(f'word{i}' for i in range(2047)))
    with pytest.raises(ValueError, match='2048'):
        load_wordlist(str(bad))


def test_load_nonexistent():
    with pytest.raises(FileNotFoundError):
        load_wordlist('/tmp/nonexistent_wordlist_xyz.txt')


@pytest.mark.parametrize('vector_idx', range(9))
def test_trezor_vectors(trezor_vectors, english_wordlist, vector_idx):
    vector = trezor_vectors[vector_idx]
    entropy_hex, expected_mnemonic, _, _ = vector
    mnemonic = entropy_to_mnemonic(entropy_hex, english_wordlist)
    assert mnemonic == expected_mnemonic


def test_mnemonic_12_words(trezor_vectors, english_wordlist):
    for v in trezor_vectors:
        if len(v[1].split()) == 12:
            mnemonic = entropy_to_mnemonic(v[0], english_wordlist)
            assert len(mnemonic.split()) == 12
            break


def test_mnemonic_18_words(trezor_vectors, english_wordlist):
    for v in trezor_vectors:
        if len(v[1].split()) == 18:
            mnemonic = entropy_to_mnemonic(v[0], english_wordlist)
            assert len(mnemonic.split()) == 18
            break


def test_mnemonic_24_words(trezor_vectors, english_wordlist):
    for v in trezor_vectors:
        if len(v[1].split()) == 24:
            mnemonic = entropy_to_mnemonic(v[0], english_wordlist)
            assert len(mnemonic.split()) == 24
            break


def test_custom_wordlist_mapping(tmp_path):
    # 2048 pseudo-random words
    custom_words = [f'xword{i:04d}' for i in range(2048)]
    custom = tmp_path / 'custom2048.txt'
    custom.write_text('\n'.join(custom_words))
    wl = load_wordlist(str(custom))
    # index 0 → 'xword0000', index 2047 → 'xword2047'
    assert indices_to_mnemonic([0, 1, 2047], wl) == 'xword0000 xword0001 xword2047'


def test_verify_with_mnemonic_library(trezor_vectors, english_wordlist):
    pytest.importorskip('mnemonic')
    from mnemonic import Mnemonic
    m = Mnemonic('english')
    for v in trezor_vectors[:3]:
        phrase = entropy_to_mnemonic(v[0], english_wordlist)
        assert m.check(phrase), f'Failed to verify: {phrase}'
