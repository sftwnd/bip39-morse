import hashlib
from importlib import resources
from pathlib import Path


def load_wordlist(source: str) -> list[str]:
    if source == 'english':
        text = (resources.files('bip39_morse.wordlists') / 'english.txt').read_text(encoding='utf-8')
    elif source == 'russian':
        text = (resources.files('bip39_morse.wordlists') / 'russian.txt').read_text(encoding='utf-8')
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f'Wordlist file not found: {source}')
        text = path.read_text(encoding='utf-8')

    words = [w.strip() for w in text.splitlines() if w.strip()]
    if len(words) != 2048:
        raise ValueError(
            f'Wordlist must contain exactly 2048 words, got {len(words)}: {source}'
        )
    return words


def entropy_to_mnemonic(entropy_hex: str, wordlist: list[str]) -> str:
    entropy_bytes = bytes.fromhex(entropy_hex)
    entropy_bits = len(entropy_bytes) * 8
    cs_len = entropy_bits // 32

    bits = bin(int(entropy_hex, 16))[2:].zfill(entropy_bits)
    digest = hashlib.sha256(entropy_bytes).digest()
    cs_bits = bin(digest[0])[2:].zfill(8)[:cs_len]

    total = bits + cs_bits
    n_words = len(total) // 11
    indices = [int(total[i*11:(i+1)*11], 2) for i in range(n_words)]
    return ' '.join(wordlist[i] for i in indices)


def indices_to_mnemonic(indices: list[int], wordlist: list[str]) -> str:
    return ' '.join(wordlist[i] for i in indices)
