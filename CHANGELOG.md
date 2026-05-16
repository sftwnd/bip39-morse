# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `examples/greek.txt` — ITU-R M.1677-1 Greek alphabet (Α–Ω, 24 letters)
  as a standalone `locale: el`. Greek's Ε and Τ cover the 1-bit codes 0
  and 1, so reverse-mode decoding has the same letter-only round-trip
  guarantee as the built-in en/ru locales. Includes final sigma ς as an
  encode-only convenience entry sharing σ's code (medial σ wins in
  reverse direction). Closes #6.
- `examples/polish.txt` — ITU-R M.1677-1 Polish accent extension under
  `locale: en` (Ą, Ć, Ę, Ł, Ń, Ó, Ś, Ź, Ż). Layers onto the built-in
  English alphabet exactly like the existing German / French / Spanish
  extensions. Six of nine characters share their bit-string with letters
  in the other shipped extensions; the load-order rule that decides who
  "wins" in reverse mode is documented in the file header and the README.
  Closes #5.

### CI
- Bump `actions/checkout` v4 → v6 and `actions/setup-python` v5 → v6 in
  `.github/workflows/tests.yml`. Both v6 majors run on Node.js 24,
  silencing the Node 20 deprecation warning and future-proofing CI past
  GitHub's September 2026 Node 20 removal. Closes #12.

### Tests
- Reach 100% line coverage of the core modules (`bip39`, `bitstream`,
  `morse`, `reverse`). Adds defensive-guard tests for early-exit branches
  in `BitStream.checksum_bits`/`entropy_hex_groups`/`indices` and
  `WordEntry.commit_current`/`pop`, plus two tests that exercise the
  `bits_to_text` letter → digit → punctuation fallback chain (and the
  final `ValueError`) via a synthetic single-letter locale. Closes #10.

## [1.0.0] — 2026-05-16

First public release.

### Added
- Interactive TUI (`prompt_toolkit`) that converts a Morse-typed phrase
  into a BIP39 mnemonic — **forward mode** (`bip39-morse`,
  `python -m bip39_morse`).
- **Reverse mode** (`--reverse`): type BIP39 words with prefix
  autocompletion, render the resulting bits as Morse-decoded text.
- Layered per-locale Morse registry (`bip39_morse/morse.py`) with
  built-in `en` (Latin, 26 codes) and `ru` (Cyrillic, 33 codes including
  `ё`).
- `--morse-table PATH` flag (repeatable) to load extra Morse alphabets
  at runtime. Later files override earlier ones for any character
  defined more than once.
- Shipping example tables: `examples/japanese.txt` (Wabun, `locale: jp`),
  `examples/german.txt`, `examples/french.txt`, `examples/spanish.txt`
  — the latter three layer onto `locale: en` and add ITU-R M.1677-1
  accented letters.
- Wordlists bundled: English (default) and Russian BIP39 wordlists. Custom
  2048-word files can be passed via `--wordlist <path>`.
- `--length` flag: `12`, `18`, or `24` (default `24`); `--lang` to pick
  the output Morse locale for reverse mode.
- `--group-size N` and `--per-line N` to format reverse-mode output
  into N-character groups and break lines after every N groups.
- `--ascii` flag for terminals without UTF-8 emoji support.
- Live hex view of accumulated entropy (`entropy_hex │ checksum_bits`
  once the green threshold is reached).
- Bulk paste support (Cmd/Ctrl+V) in both modes — unsupported
  characters are skipped with a hint; reverse mode resolves each token
  as exact word or unique prefix.
- Round-trip self-check workflow documented in the README — forward →
  reverse → forward must reproduce the same entropy hex.
- Animated demos in `docs/` (forward + reverse, asciinema casts + SVG +
  PNG), built by `docs/generate_demo.py` using the iroha as a public
  pangram of the kana.
- Test suite (`pytest` + `pytest-cov`) with 245 tests covering
  `morse`, `bitstream`, `bip39`, and `reverse`; coverage floor set to
  85% in `pyproject.toml`. Includes official Trezor BIP39 test vectors
  at `tests/vectors/trezor_vectors.json`.
- CI workflow `.github/workflows/tests.yml` running pytest on Python
  3.11 for every push and PR against `master`.
- MIT License with donation channels (BTC + USDC) in `LICENSE.md`.

### Security
- No entropy is written to disk at runtime.
- No network calls at runtime.
- No randomness injected — all entropy comes from the user's typed
  phrase. README ships an explicit *Security warning* section about
  running this on a clean live OS for any real seed generation.

[Unreleased]: https://github.com/sftwnd/bip39-morse/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/sftwnd/bip39-morse/releases/tag/v1.0.0
