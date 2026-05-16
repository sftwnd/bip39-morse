"""Reverse-mode word entry: user types BIP39 words with autocomplete,
the model accumulates indices and exposes the resulting bit stream."""
import re
from dataclasses import dataclass, field

_PASTE_SEPARATORS = re.compile(r'[ \t\r\n]+')


@dataclass
class WordEntry:
    wordlist: list[str]
    target_words: int

    _completed: list[str] = field(default_factory=list, init=False)
    _current: str = field(default='', init=False)
    _index_lookup: dict[str, int] = field(default=None, init=False)
    _wordset: set[str] = field(default=None, init=False)

    def __post_init__(self) -> None:
        self._index_lookup = {w: i for i, w in enumerate(self.wordlist)}
        self._wordset = set(self.wordlist)

    @property
    def completed(self) -> list[str]:
        return list(self._completed)

    @property
    def current(self) -> str:
        return self._current

    @property
    def is_ready(self) -> bool:
        return len(self._completed) >= self.target_words

    def candidates(self, limit: int = 8) -> list[str]:
        """Words from the wordlist starting with current prefix (capped at `limit`).
        If the current input is empty, returns the first `limit` words of the wordlist
        so the user has an immediate hint at the start of a new word."""
        if not self._current:
            return list(self.wordlist[:limit])
        out: list[str] = []
        for w in self.wordlist:
            if w.startswith(self._current):
                out.append(w)
                if len(out) >= limit:
                    break
        return out

    def push_char(self, ch: str) -> str:
        """Append a character to the current word. If the resulting prefix
        matches exactly one wordlist entry, the current word is auto-completed
        and committed. Returns:
          'ok'        — char accepted, no auto-completion
          'completed' — current word auto-completed and committed
          'rejected'  — char would leave zero candidates; nothing changed
          'full'      — already have target_words; nothing changed
        """
        if self.is_ready:
            return 'full'
        new_current = self._current + ch
        matches = [w for w in self.wordlist if w.startswith(new_current)]
        if not matches:
            return 'rejected'
        if len(matches) == 1:
            self._completed.append(matches[0])
            self._current = ''
            return 'completed'
        self._current = new_current
        return 'ok'

    def commit_current(self) -> bool:
        """If the current input exactly matches a wordlist word, commit it.
        Useful when the word is also a prefix of longer words (e.g. 'van'
        vs 'vanish') and auto-completion did not fire. Returns True on commit.
        """
        if self.is_ready:
            return False
        if self._current and self._current in self._wordset:
            self._completed.append(self._current)
            self._current = ''
            return True
        return False

    def pop(self) -> bool:
        """Remove one character. If current word is empty, pop the last
        completed word back into the current buffer minus its last char.
        Returns True if anything changed.
        """
        if self._current:
            self._current = self._current[:-1]
            return True
        if self._completed:
            last = self._completed.pop()
            self._current = last[:-1]
            return True
        return False

    def paste_text(self, text: str) -> tuple[int, str | None]:
        """Process pasted text containing wordlist words separated by any of
        space, tab, CR, LF. Each token may be either a full wordlist word or
        a prefix that uniquely identifies one. The first token is prepended
        with the current partial input (if any). Stops at the first
        unresolvable token.

        Returns (committed_count, failed_token):
          - failed_token is None on full success;
          - failed_token is the offending string on the first failure
            (zero matches, or ambiguous prefix that is not itself a word).
        """
        tokens = [t for t in _PASTE_SEPARATORS.split(text.strip()) if t]
        if not tokens:
            return 0, None
        if self._current:
            tokens[0] = self._current + tokens[0]
            self._current = ''
        committed = 0
        for tok in tokens:
            if self.is_ready:
                break
            # Exact match wins even when prefix-of-other ('van' vs 'vanish'):
            # the pasted token represents what the user actually copied.
            if tok in self._wordset:
                self._completed.append(tok)
                committed += 1
                continue
            matches = [w for w in self.wordlist if w.startswith(tok)]
            if len(matches) == 1:
                self._completed.append(matches[0])
                committed += 1
                continue
            return committed, tok
        return committed, None

    def bits(self) -> str:
        """Concatenated 11-bit indices of all completed words."""
        return ''.join(
            format(self._index_lookup[w], '011b') for w in self._completed
        )

    def entropy_bits_str(self, entropy_bits: int) -> str:
        """First `entropy_bits` bits of the accumulated word indices.
        Returns whatever is accumulated so far if shorter than entropy_bits."""
        b = self.bits()
        return b[:entropy_bits]
