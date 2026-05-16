import pytest
from bip39_morse.reverse import WordEntry, format_grouped
from bip39_morse.morse import bits_to_text, char_to_bits
from bip39_morse.bip39 import load_wordlist


@pytest.fixture
def wl_en():
    return load_wordlist('english')


@pytest.fixture
def wl_ru():
    return load_wordlist('russian')


def test_autocomplete_on_unique_prefix(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    # 'aba' uniquely matches 'abandon'
    for ch in 'aba':
        entry.push_char(ch)
    assert entry.completed == ['abandon']
    assert entry.current == ''


def test_partial_input_keeps_state(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    entry.push_char('a')
    # 'a' has many matches
    cands = entry.candidates(limit=8)
    assert len(cands) == 8
    assert entry.current == 'a'
    assert entry.completed == []


def test_candidates_limit(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    entry.push_char('a')
    entry.push_char('b')  # 'ab*' — could be many
    cands = entry.candidates(limit=8)
    assert len(cands) <= 8
    for c in cands:
        assert c.startswith('ab')


def test_candidates_empty_returns_first_n(wl_en):
    """When no input yet, the first words of the wordlist are suggested as a hint."""
    entry = WordEntry(wordlist=wl_en, target_words=12)
    cands = entry.candidates(limit=8)
    assert cands == wl_en[:8]


def test_candidates_after_commit_returns_first_n(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    for ch in 'aba':
        entry.push_char(ch)
    assert entry.completed == ['abandon']
    assert entry.current == ''
    cands = entry.candidates(limit=8)
    assert cands == wl_en[:8]


def test_rejected_no_match(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    # 'q' followed by 'z' has no word
    entry.push_char('q')
    status = entry.push_char('z')
    assert status == 'rejected'
    assert entry.current == 'q'


def test_pop_within_current(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    entry.push_char('a')
    entry.push_char('b')
    entry.pop()
    assert entry.current == 'a'


def test_pop_from_completed(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    for ch in 'aba':
        entry.push_char(ch)
    assert entry.completed == ['abandon']
    entry.pop()
    assert entry.completed == []
    assert entry.current == 'abando'


def test_is_ready_after_target(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=2)
    for ch in 'aba':
        entry.push_char(ch)
    assert not entry.is_ready
    for ch in 'abi':  # 'ability'
        entry.push_char(ch)
    assert entry.is_ready


def test_bits_concatenation(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=2)
    # 'abandon' = index 0, 'ability' = index 1
    for ch in 'aba':
        entry.push_char(ch)
    for ch in 'abi':
        entry.push_char(ch)
    assert entry.bits() == '0' * 11 + '0' * 10 + '1'


def test_commit_current_for_prefix_word(wl_en):
    """'van' is a word AND a prefix of 'vanish'; auto-complete doesn't fire."""
    entry = WordEntry(wordlist=wl_en, target_words=12)
    for ch in 'van':
        entry.push_char(ch)
    # Auto-complete didn't fire because 'van' is also prefix of 'vanish'
    assert entry.current == 'van'
    assert entry.completed == []
    # Explicit commit succeeds
    assert entry.commit_current() is True
    assert entry.completed == ['van']
    assert entry.current == ''


def test_commit_current_no_op_when_not_exact_match(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    for ch in 'va':  # 'va' is not itself a wordlist word
        entry.push_char(ch)
    assert entry.commit_current() is False
    assert entry.current == 'va'
    assert entry.completed == []


def test_commit_current_no_op_when_empty(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    assert entry.commit_current() is False


def test_commit_current_no_op_when_ready(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=1)
    for ch in 'aba':  # commits 'abandon', entry becomes ready
        entry.push_char(ch)
    assert entry.is_ready
    assert entry.commit_current() is False


def test_pop_no_op_on_fully_empty(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    assert entry.pop() is False


def test_full_blocks_input(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=1)
    for ch in 'aba':
        entry.push_char(ch)
    assert entry.is_ready
    status = entry.push_char('a')
    assert status == 'full'


def test_paste_full_words(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    committed, failed = entry.paste_text('abandon ability able')
    assert failed is None
    assert committed == 3
    assert entry.completed == ['abandon', 'ability', 'able']


def test_paste_unique_prefixes(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    # 'aba'→abandon (unique), 'abi'→ability (unique), 'abl'→able (unique)
    committed, failed = entry.paste_text('aba abi abl')
    assert failed is None
    assert committed == 3
    assert entry.completed == ['abandon', 'ability', 'able']


def test_paste_mixed_separators(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    committed, failed = entry.paste_text('abandon\tability\nable\r\nabout\nabove')
    assert failed is None
    assert committed == 5
    assert entry.completed == ['abandon', 'ability', 'able', 'about', 'above']


def test_paste_exact_word_when_prefix_of_others(wl_en):
    """'van' is a word and a prefix of 'vanish'; pasting 'van' must yield 'van'."""
    entry = WordEntry(wordlist=wl_en, target_words=12)
    committed, failed = entry.paste_text('van')
    assert failed is None
    assert entry.completed == ['van']


def test_paste_stops_on_ambiguous(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    # 'a' has many matches and isn't itself a word
    committed, failed = entry.paste_text('abandon a ability')
    assert committed == 1
    assert failed == 'a'
    assert entry.completed == ['abandon']


def test_paste_stops_on_unknown(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    committed, failed = entry.paste_text('abandon zzzzzz ability')
    assert committed == 1
    assert failed == 'zzzzzz'


def test_paste_consumes_current_buffer(wl_en):
    """Paste prepends existing partial input onto the first token."""
    entry = WordEntry(wordlist=wl_en, target_words=12)
    entry.push_char('a')  # current = 'a'
    committed, failed = entry.paste_text('bandon ability')
    assert failed is None
    # 'a'+'bandon' = 'abandon' (unique)
    assert entry.completed == ['abandon', 'ability']
    assert entry.current == ''


def test_paste_respects_target_limit(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=2)
    committed, failed = entry.paste_text('abandon ability able')
    # Only 2 should commit; rest skipped silently after `is_ready`.
    assert committed == 2
    assert entry.is_ready


def test_paste_empty_text(wl_en):
    entry = WordEntry(wordlist=wl_en, target_words=12)
    committed, failed = entry.paste_text('   \t\n  ')
    assert committed == 0
    assert failed is None


def test_reverse_bits_to_text_decodable_to_same_entropy(wl_en):
    """Reverse mode: bits → text. Re-encoding the text via forward Morse
    must reproduce the original entropy bits as a prefix."""
    entry = WordEntry(wordlist=wl_en, target_words=12)
    # Enter 12 words: 'abandon' (0) twelve times → 132 zero bits
    for _ in range(12):
        for ch in 'aba':
            entry.push_char(ch)
    assert entry.is_ready
    entropy = entry.entropy_bits_str(128)
    assert entropy == '0' * 128
    text = bits_to_text(entropy, locale='en')
    re_bits = ''.join(char_to_bits(c) for c in text)
    assert re_bits[:128] == '0' * 128


def test_reverse_russian_uses_cyrillic_decoding(wl_ru):
    entry = WordEntry(wordlist=wl_ru, target_words=12)
    # 'абзац' uniquely matches with 'абз' (assume — depends on wordlist).
    # Use a known prefix from Russian wordlist: 'абз' might still be ambiguous.
    # Just type enough chars from first word until commit:
    n_committed_before = 0
    for ch in wl_ru[0]:
        entry.push_char(ch)
        if len(entry.completed) > n_committed_before:
            n_committed_before = len(entry.completed)
            break
    assert len(entry.completed) == 1
    bits = entry.bits()
    text = bits_to_text(bits, locale='ru')
    # All decoded chars should be Cyrillic letters, digits or punctuation
    for c in text:
        assert c.isalpha() and ord(c) > 127 or c in '0123456789.,-!?:'


# --- format_grouped --------------------------------------------------------

def test_format_grouped_default_five():
    assert format_grouped('ABCDEFGHIJ') == 'ABCDE FGHIJ'


def test_format_grouped_custom_size():
    assert format_grouped('ABCDEFGHIJ', group_size=4) == 'ABCD EFGH IJ'


def test_format_grouped_trailing_partial():
    assert format_grouped('ABCDEFG', group_size=5) == 'ABCDE FG'


def test_format_grouped_short_text():
    assert format_grouped('ABC', group_size=5) == 'ABC'


def test_format_grouped_empty():
    assert format_grouped('') == ''


def test_format_grouped_group_size_one():
    assert format_grouped('ABCD', group_size=1) == 'A B C D'


def test_format_grouped_per_line():
    text = 'ABCDEFGHIJKLMNOPQRSTUVWX'  # 24 chars
    # group_size=4, per_line=3 → 6 groups, 2 lines of 3 groups
    out = format_grouped(text, group_size=4, per_line=3)
    assert out == 'ABCD EFGH IJKL\nMNOP QRST UVWX'


def test_format_grouped_per_line_uneven():
    text = 'ABCDEFGHIJKLMNOP'  # 16 chars
    # group_size=5: 'ABCDE FGHIJ KLMNO P'; per_line=2 → split after 2 groups
    out = format_grouped(text, group_size=5, per_line=2)
    assert out == 'ABCDE FGHIJ\nKLMNO P'


def test_format_grouped_per_line_one():
    """per_line=1 puts each group on its own line."""
    out = format_grouped('ABCDEFGHIJ', group_size=5, per_line=1)
    assert out == 'ABCDE\nFGHIJ'


def test_format_grouped_invalid_group_size():
    with pytest.raises(ValueError, match='group_size'):
        format_grouped('ABC', group_size=0)
    with pytest.raises(ValueError, match='group_size'):
        format_grouped('ABC', group_size=-1)


def test_format_grouped_invalid_per_line():
    with pytest.raises(ValueError, match='per_line'):
        format_grouped('ABC', group_size=5, per_line=0)
    with pytest.raises(ValueError, match='per_line'):
        format_grouped('ABC', group_size=5, per_line=-1)
