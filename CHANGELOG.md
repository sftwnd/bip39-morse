# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
