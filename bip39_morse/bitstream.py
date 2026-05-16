import hashlib
from dataclasses import dataclass, field


@dataclass
class BitStream:
    entropy_bits: int

    _bits: str = field(default='', init=False)
    _stack: list = field(default_factory=list, init=False)

    def push(self, char_displayed: str, bits_added: str) -> None:
        self._stack.append((char_displayed, bits_added))
        self._bits += bits_added

    def pop(self) -> tuple[str, str] | None:
        if not self._stack:
            return None
        char_displayed, bits_added = self._stack.pop()
        self._bits = self._bits[: len(self._bits) - len(bits_added)]
        return char_displayed, bits_added

    @property
    def accumulated_bits(self) -> int:
        return len(self._bits)

    @property
    def is_ready(self) -> bool:
        return self.accumulated_bits >= self.entropy_bits

    def _entropy_bytes(self) -> bytes:
        eb = self._bits[: self.entropy_bits]
        # Pad to full bytes
        padded = eb.ljust((len(eb) + 7) // 8 * 8, '0')
        return int(padded, 2).to_bytes(len(padded) // 8, 'big')

    def checksum_bits(self) -> str:
        if not self.is_ready:
            return ''
        cs_len = self.entropy_bits // 32
        digest = hashlib.sha256(self._entropy_bytes()).digest()
        first_byte = digest[0]
        # Take top cs_len bits from first byte
        bits = ''
        for i in range(7, 7 - cs_len, -1):
            bits += str((first_byte >> i) & 1)
        return bits

    def entropy_hex_groups(self) -> str:
        if self.entropy_bits == 0:
            return ''
        eb = self._bits[: self.entropy_bits]
        padded = eb.ljust(self.entropy_bits, '0')
        n_bytes = self.entropy_bits // 8
        val = int(padded, 2)
        hex_str = format(val, f'0{n_bytes * 2}X')
        # Group by 4 hex chars (16 bits)
        groups = [hex_str[i:i+4] for i in range(0, len(hex_str), 4)]
        return ' '.join(groups)

    def partial_hex_groups(self) -> str:
        """Hex of completed bytes only (for state A)."""
        n_complete = len(self._bits) // 8
        if n_complete == 0:
            return ''
        bits_complete = self._bits[: n_complete * 8]
        val = int(bits_complete, 2)
        hex_str = format(val, f'0{n_complete * 2}X')
        groups = [hex_str[i:i+4] for i in range(0, len(hex_str), 4)]
        return ' '.join(groups)

    def hex_display(self) -> str:
        if self.is_ready:
            entropy_hex = self.entropy_hex_groups()
            cs = self.checksum_bits()
            return f'{entropy_hex} │ {cs}'
        return self.partial_hex_groups()

    def visual_buffer(self) -> str:
        return ''.join(ch for ch, _ in self._stack)

    def normalized_input(self) -> str:
        return ' '.join(self.visual_buffer().upper().split())

    def indices(self) -> list[int]:
        if not self.is_ready:
            return []
        cs = self.checksum_bits()
        total = self._bits[: self.entropy_bits] + cs
        n_words = len(total) // 11
        return [int(total[i*11:(i+1)*11], 2) for i in range(n_words)]
