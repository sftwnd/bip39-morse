import pytest
from bip39_morse.bitstream import BitStream
from bip39_morse.morse import char_to_bits


def make_stream(n_words: int = 12) -> BitStream:
    lengths = {12: 128, 18: 192, 24: 256}
    return BitStream(entropy_bits=lengths[n_words])


def test_empty_stream():
    s = make_stream(12)
    assert s.accumulated_bits == 0
    assert s.hex_display() == ''
    assert not s.is_ready


def test_accumulate_bits():
    s = make_stream(12)
    s.push('a', char_to_bits('a'))  # '01' = 2 bits
    assert s.accumulated_bits == 2
    assert s.hex_display() == ''  # no complete bytes yet


def test_hex_appears_after_full_byte():
    s = make_stream(12)
    # 't' = '1' (1 bit), push 8 times to get 8 bits
    for _ in range(8):
        s.push('t', '1')
    assert s.accumulated_bits == 8
    assert s.hex_display() == 'FF'


def test_hex_groups_by_4():
    s = make_stream(12)
    # Push 16 bits = 2 bytes
    for _ in range(16):
        s.push('t', '1')
    assert s.hex_display() == 'FFFF'


def test_backspace_no_op_on_empty():
    s = make_stream(12)
    result = s.pop()
    assert result is None
    assert s.accumulated_bits == 0


def test_backspace_removes_last_char():
    s = make_stream(12)
    s.push('a', '01')
    s.push('b', '1000')
    assert s.accumulated_bits == 6
    s.pop()
    assert s.accumulated_bits == 2
    s.pop()
    assert s.accumulated_bits == 0


def test_backspace_hex_consistent():
    s = make_stream(12)
    for _ in range(8):
        s.push('t', '1')
    assert 'FF' in s.hex_display()
    s.pop()  # remove one 't'
    assert s.accumulated_bits == 7
    assert s.hex_display() == ''  # no complete bytes


def test_big_endian_packing():
    s = make_stream(12)
    # 'e' = '.' = '0' and 't' = '-' = '1'
    # Push 8 bits: 01010101 = 0x55
    for ch, bits in [('e', '0'), ('t', '1')] * 4:
        s.push(ch, bits)
    assert s.accumulated_bits == 8
    assert s.hex_display() == '55'


def test_threshold_transition():
    s = make_stream(12)
    assert not s.is_ready
    # Fill exactly 128 bits
    for _ in range(128):
        s.push('e', '0')
    assert s.accumulated_bits == 128
    assert s.is_ready
    display = s.hex_display()
    assert '│' in display
    assert len(s.checksum_bits()) == 4  # 128/32 = 4


def test_checksum_disappears_on_backtrack():
    s = make_stream(12)
    for _ in range(128):
        s.push('e', '0')
    assert s.is_ready
    s.pop()
    assert not s.is_ready
    assert '│' not in s.hex_display()


def test_extra_input_beyond_threshold():
    s = make_stream(12)
    for _ in range(128):
        s.push('e', '0')
    cs1 = s.checksum_bits()
    hex1 = s.hex_display()
    s.push('t', '1')
    assert s.checksum_bits() == cs1
    assert s.hex_display() == hex1


def test_space_pushes_empty_bits():
    s = make_stream(12)
    s.push(' ', '')
    assert s.accumulated_bits == 0
    s.pop()
    assert s.accumulated_bits == 0


def test_visual_buffer():
    s = make_stream(12)
    s.push('H', char_to_bits('h'))
    s.push('i', char_to_bits('i'))
    assert s.visual_buffer() == 'Hi'


def test_normalized_input():
    s = make_stream(12)
    for ch in 'Привет, мир!':
        s.push(ch, char_to_bits(ch) if ch != ' ' else '')
    assert s.normalized_input() == 'ПРИВЕТ, МИР!'


def test_normalized_collapses_multiple_spaces():
    s = make_stream(12)
    for ch in 'a   b  c':
        s.push(ch, char_to_bits(ch) if ch != ' ' else '')
    assert s.normalized_input() == 'A B C'


def test_normalized_trims_edges():
    s = make_stream(12)
    for ch in '  hi  ':
        s.push(ch, char_to_bits(ch) if ch != ' ' else '')
    assert s.normalized_input() == 'HI'


def test_indices_count():
    s = make_stream(12)
    for _ in range(128):
        s.push('e', '0')
    assert len(s.indices()) == 12


def test_indices_18():
    s = make_stream(18)
    for _ in range(192):
        s.push('e', '0')
    assert len(s.indices()) == 18


def test_indices_24():
    s = make_stream(24)
    for _ in range(256):
        s.push('e', '0')
    assert len(s.indices()) == 24


def test_checksum_bits_empty_when_not_ready():
    s = make_stream(12)
    assert not s.is_ready
    assert s.checksum_bits() == ''


def test_indices_empty_when_not_ready():
    s = make_stream(12)
    assert not s.is_ready
    assert s.indices() == []


def test_entropy_hex_groups_empty_when_entropy_bits_zero():
    s = BitStream(entropy_bits=0)
    assert s.entropy_hex_groups() == ''
