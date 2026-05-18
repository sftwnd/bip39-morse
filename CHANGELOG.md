# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation
- README: new *Why Morse code?* section explaining the rationale for
  using Morse as the entropy bridge — bit-level isomorphism with `.` /
  `-`, paper-auditable ITU-R M.1677-1 table, exact round-trip via the
  `E` / `T` single-bit codes, memorable-phrase tradeoffs with the
  explicit entropy-quality caveat, and locale-pluggable design. Placed
  between *Security warning* and *How it works* so rationale precedes
  the mechanical description. Mirrored in `README.ru.md`. Closes #23.

## [1.0.3] — 2026-05-20

Locale-aware encoding + ASCII-fold + parity infrastructure for the
[iOS port](https://github.com/sftwnd/bip39-morse-ios). No breaking
changes for callers that don't pass new optional parameters.

### Added
- `PUNCTUATION` map расширена до 10 знаков (#25):
  - ITU-R M.1677-1 §1.1.3: `.`, `,`, `-`, `?`, `:`.
  - American Morse extensions (default-on): `!`, `_`, `$`, `&`, `;` —
    стандартизированы не в ITU-R а в американской радиопрактике.
    Раньше включался только `!` без явной маркировки. Зеркало
    `american_extensions.txt` в iOS-проекте (там opt-in флагом).
- `char_to_bits(ch, fold_diacritics=True)` — ASCII-fold через NFKD +
  strip combining marks для символов отсутствующих в Morse-таблицах
  (`é → e`, `š → s`, `ñ → n`, `ÿ → y`). Multi-char folds (`ß → ss`) и
  non-Latin (`中`, `ا`) остаются raise. CLI: `--fold-diacritics`. TUI:
  `allowed_chars(fold_diacritics=True)` расширяет keystroke whitelist
  до общего набора латинских диакритик чьи base-формы есть в реестре.
  (#27)
- `char_to_bits(ch, locale=...)` — locale-aware encoding. При заданной
  локали поиск идёт сначала в её layer-table — это позволяет ru-локали
  иметь свою советскую пунктуацию без конфликта с международными
  кодами под другими локалями. CLI: `--input-locale LOCALE`. TUI:
  `input_locale` параметр пробрасывается в keystroke handler. (#29)
- Soviet `.` (`......`) и `,` (`.-.-.-`) добавлены в `CYRILLIC` —
  доступны через `char_to_bits(ch, locale='ru')`. Зеркало
  `russian.txt` в iOS-проекте. (#29)
- Cross-language Morse parity infrastructure (#30):
  - `tests/generate_morse_parity_vectors.py` — генератор 178 vectors
    `(input_char, locale, fold) → expected_bits`, покрывающих все
    built-in алфавиты, диакритические extensions, советскую
    пунктуацию, fold cases и edge errors.
  - `tests/vectors/morse_parity_vectors.json` — generated fixture.
  - `tests/test_parity_vectors.py` — self-consistency check (если
    `morse.py` меняется без regen JSON — тест падает с указанием
    как пересобрать).
  - Тот же JSON consumed iOS-портом в
    `MorseKeyTests/MorseParityVectorsTests.swift` —
    cross-language conformance проверяется в CI обеих сторон.

### Changed
- **`char_to_bits` lookup order при `locale=None`**: `DIGITS >
  PUNCTUATION > forward_table()` (вместо прежнего `forward_table >
  DIGITS > PUNCTUATION`). Это сохраняет международные ITU-R коды для
  `.` и `,` после добавления советских в `CYRILLIC` — без передачи
  `locale` поведение для пунктуации не меняется. Буквы/цифры/акценты
  не затронуты (они не в `DIGITS`/`PUNCTUATION`). (#29)

### Tests
- 360 tests pass (was 320 in 1.0.2), 100% coverage maintained.
- New: punctuation extensions, ASCII-fold (parametric +
  multi-char/non-Latin edge cases), locale-aware encoding (Soviet vs
  international, fallback paths, round-trip), parity-vectors
  self-consistency.

## [1.0.2] — 2026-05-17

First release published to PyPI. Strictly a packaging / branding /
infrastructure release — no runtime behaviour changes since 1.0.1.

### Packaging
- PyPI publishing infrastructure via OIDC trusted publishing (no
  long-lived token in repo secrets). Two new workflows:
  `.github/workflows/release-testpypi.yml` (manual `workflow_dispatch`
  trigger, publishes to TestPyPI, sigstore attestations off because
  TestPyPI's PEP 740 support is unreliable) and
  `.github/workflows/release-pypi.yml` (triggers on
  `release: published` from the Releases UI, publishes to production
  PyPI with sigstore attestations on). Each workflow splits build from
  publish so the upload step has no source checkout.
- `pyproject.toml` brought up to PyPI-publication standard: adds
  `authors`, `keywords`, twelve `classifiers` (Development Status 5,
  License, supported Python versions 3.11–3.13, Topic :: Security ::
  Cryptography, etc.), and `[project.urls]` (Homepage, Repository,
  Issues, Changelog, Releases). Description rewritten to lead with
  the **MorseKey** brand and the offline / deterministic / open-source
  tagline.
- `README.md` and `README.ru.md`: image references converted from
  relative paths (`docs/logo.svg`, `docs/demo.svg`, etc.) to absolute
  `raw.githubusercontent.com` URLs so the logo and demos render
  correctly on the PyPI project page. Cross-link to the bilingual
  README counterpart and the license badge link also converted to
  absolute URLs. A PyPI version badge added next to the existing CI /
  release / license / Python badges.
- `docs/PUBLISHING.md` documents the one-time setup (PyPI accounts,
  2FA, GitHub environments, pending-publishers) and the per-release
  flow for both TestPyPI and production, including yank procedure and
  sigstore verification example.

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

[Unreleased]: https://github.com/sftwnd/bip39-morse/compare/v1.0.2...HEAD
[1.0.2]: https://github.com/sftwnd/bip39-morse/releases/tag/v1.0.2
[1.0.1]: https://github.com/sftwnd/bip39-morse/releases/tag/v1.0.1
[1.0.0]: https://github.com/sftwnd/bip39-morse/releases/tag/v1.0.0
