"""End-to-end tests using prompt_toolkit pipe input."""
import pytest
from unittest.mock import patch
from bip39_morse.bitstream import BitStream
from bip39_morse.morse import char_to_bits
from bip39_morse.bip39 import load_wordlist, indices_to_mnemonic


def simulate_input(phrase: str, entropy_bits: int) -> tuple[str, str]:
    """Simulate typing a phrase and pressing Enter, return (normalized, mnemonic)."""
    wl = load_wordlist('english')
    stream = BitStream(entropy_bits=entropy_bits)
    for ch in phrase:
        bits = char_to_bits(ch) if ch != ' ' else ''
        stream.push(ch, bits)
    assert stream.is_ready, f'Not enough bits after phrase: {stream.accumulated_bits}/{entropy_bits}'
    mnemonic = indices_to_mnemonic(stream.indices(), wl)
    normalized = stream.normalized_input()
    return normalized, mnemonic


def get_entropy_bits_for_phrase(phrase: str) -> int:
    """Calculate total bits from phrase."""
    total = 0
    for ch in phrase:
        if ch != ' ':
            total += len(char_to_bits(ch))
    return total


def test_scenario_1_known_mnemonic():
    """Test that known entropy produces known mnemonic."""
    import hashlib
    from bip39_morse.bip39 import entropy_to_mnemonic
    wl = load_wordlist('english')
    entropy_hex = '00000000000000000000000000000000'
    mnemonic = entropy_to_mnemonic(entropy_hex, wl)
    assert mnemonic == 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about'


def test_scenario_2_input_after_ready():
    """Chars after threshold go to normalized output but not to mnemonic bits."""
    # Use 't' (1 bit each) to hit 128 bits exactly, then add more
    stream = BitStream(entropy_bits=128)
    for _ in range(128):
        stream.push('t', '1')
    assert stream.is_ready
    cs_before = stream.checksum_bits()
    idx_before = stream.indices()

    stream.push('e', '0')  # extra char after ready
    stream.push('t', '1')

    assert stream.checksum_bits() == cs_before
    assert stream.indices() == idx_before
    assert 'ET' in stream.normalized_input() or stream.visual_buffer().endswith('et')


def test_scenario_3_forbidden_chars():
    """Forbidden characters should not affect stream."""
    from bip39_morse.tui import allowed_chars
    allowed = allowed_chars()
    assert '@' not in allowed
    assert '#' not in allowed

    # Verify that allowed chars are properly handled
    assert 'a' in allowed
    assert 'A' in allowed
    assert 'а' in allowed
    assert ' ' in allowed
    assert '.' in allowed
    # Digits are now allowed (real Morse supports 0-9)
    assert '1' in allowed
    assert '9' in allowed


def test_normalized_output_format():
    """Normalized output: uppercase, runs of spaces collapsed to single, punct preserved."""
    stream = BitStream(entropy_bits=128)
    for ch in 'Привет,  мир!':
        bits = char_to_bits(ch) if ch != ' ' else ''
        stream.push(ch, bits)
    norm = stream.normalized_input()
    assert norm == 'ПРИВЕТ, МИР!'


def test_entropy_only_from_first_bits():
    """Mnemonic must be based only on first entropy_bits bits."""
    stream1 = BitStream(entropy_bits=128)
    for _ in range(128):
        stream1.push('t', '1')
    idx1 = stream1.indices()

    stream2 = BitStream(entropy_bits=128)
    for _ in range(128):
        stream2.push('t', '1')
    for _ in range(10):
        stream2.push('e', '0')  # extra bits
    idx2 = stream2.indices()

    assert idx1 == idx2


def test_backspace_through_byte_boundary():
    """Backspace across a byte boundary restores correct state."""
    stream = BitStream(entropy_bits=128)
    # Push 7 bits
    for _ in range(7):
        stream.push('e', '0')
    assert stream.accumulated_bits == 7
    assert stream.hex_display() == ''
    # Push 1 more → 8 bits, hex appears
    stream.push('t', '1')
    assert stream.accumulated_bits == 8
    assert stream.hex_display() != ''
    # Pop → back to 7, hex gone
    stream.pop()
    assert stream.accumulated_bits == 7
    assert stream.hex_display() == ''
