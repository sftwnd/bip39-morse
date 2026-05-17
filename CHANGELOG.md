# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation
- Branding: project now carries the name **MorseKey** at the top of
  the README (the canonical package / repo / CLI name `bip39-morse` is
  unchanged — `pip install bip39-morse`, `import bip39_morse`, and the
  `bip39-morse` console script all continue to work). Adds
  `docs/logo.svg` (square app icon, used in the README header) and
  `docs/social.svg` / `docs/social.png` (1280×640 social-preview banner
  for the GitHub repo card and link previews). README and README.ru
  get an HTML header block: centred logo, MorseKey wordmark, the
  `bip39-morse` aka note, a one-line tagline
  (*BIP39 seed phrases ⇄ Morse code · offline · deterministic · open-source*),
  and CI / release / license / Python-version shields.io badges.

### Added (pending Czech-contributor review)
- `examples/czech.txt` — Czech accent extension under `locale: en`
  implementing the **drop-diacritic** convention from Czech amateur
  radio practice (cs.wikipedia.org/wiki/Morseova_abeceda), since
  ITU-R M.1677-1 does not define codes for the 15 Czech-specific
  diacritic letters. Each Czech letter (Á Č Ď É Ě Í Ň Ó Ř Š Ť Ú Ů Ý Ž)
  maps to the same bit string as its base Latin letter; reverse-mode
  decoding always picks the base Latin form. **Ships pending review by
  a Czech-speaking contributor with access to an authoritative
  national standard** — see issue #7 for the rationale. Closes #7
  on confirmation.

## [1.0.1] — 2026-05-16

### Documentation
- `CONTRIBUTING.ru.md` — full Russian translation of `CONTRIBUTING.md`,
  matching the bilingual treatment already used for the README. Both
  files now cross-link to each other at the top, mirroring the README
  pattern. The English `CONTRIBUTING.md` was also brought up to date —
  the *Adding a Morse locale* table now lists the Greek (`el`) and
  Polish entries that have shipped since the file was first written.
  Closes #9.

### Fixed
- **Safety: ß / SS round-trip mismatch in reverse mode.** Python's
  `str.upper()` maps lowercase `ß` to the two-character string `'SS'`,
  which silently broke the forward/reverse bit-level round-trip — `ß`'s
  7-bit code `...--..` became a 6-bit `'SS'` on re-encoding. Any German
  passphrase containing `ß` would have caused the README's
  "round-trip self-check" safety workflow to fail. `bits_to_text` now
  emits `ẞ` (U+1E9E LATIN CAPITAL LETTER SHARP S) for that bit pattern,
  restoring the round-trip invariant. Discovered by the new
  hypothesis-based property tests added in this release. Closes #8
  alongside the property-tests work.

### Tests
- Property-based round-trip tests using `hypothesis` for the
  `bits_to_text → char_to_bits` invariant. For random 128 / 192 / 256-bit
  strings, feeding the reverse-decoded text back through forward mode
  must reproduce the exact same bit string. Parametrised over the
  built-in `en` / `ru` locales, the shipped Greek `el`, every individual
  Latin accent extension layered over `en`, and the worst-case
  "all four Latin extensions loaded together" stack. Uses
  `@settings(derandomize=True)` so each run replays the same examples
  for CI reproducibility; override locally with
  `pytest --hypothesis-seed=random` for exploratory fuzzing. Adds
  `hypothesis>=6.0` to the test extras. Closes #8.

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

[Unreleased]: https://github.com/sftwnd/bip39-morse/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/sftwnd/bip39-morse/releases/tag/v1.0.1
[1.0.0]: https://github.com/sftwnd/bip39-morse/releases/tag/v1.0.0
