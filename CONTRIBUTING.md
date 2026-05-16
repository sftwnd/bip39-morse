# Contributing to bip39-morse

Thanks for considering a contribution. This project is small and focused, so
the contribution surface is well-defined — please skim this document before
opening an issue or PR.

## Ways to contribute

- **Bug reports.** Open an issue using the *Bug report* template.
- **Feature requests.** Use the *Feature request* template. Please keep in
  mind the security posture of the tool (see below) — features that involve
  network access, persistent storage of entropy, or randomness injection are
  out of scope by design.
- **New Morse locale tables.** This is the most natural contribution path —
  the tool is built around a pluggable per-locale Morse registry. Use the
  *New Morse locale* issue template, then submit the table file under
  `examples/<locale>.txt`. See [Adding a Morse locale](#adding-a-morse-locale).
- **Documentation.** README, README.ru, code comments, examples — all welcome.
  The Russian README should stay in sync with the English one for any
  user-facing change.
- **Tests.** New test vectors, edge cases, fuzz-style inputs for the bit
  pipeline, additional Trezor / BIP39 vectors — all welcome.

## Development setup

Requires Python 3.11+.

```bash
git clone https://github.com/sftwnd/bip39-morse.git
cd bip39-morse
python -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
```

Run the tool locally:

```bash
bip39-morse --length 12
python -m bip39_morse --reverse --length 12
```

## Running tests

```bash
pytest
```

Coverage is enforced at **85%** for `morse`, `bitstream`, `bip39`, and
`reverse` modules (see `pyproject.toml` → `[tool.coverage.report]`). The TUI
modules (`tui.py`, `tui_reverse.py`) and the CLI entrypoint are excluded from
coverage because they are driven by `prompt_toolkit` and tested through
`test_e2e.py` separately.

If your change touches the bit pipeline, please add a test in
`tests/test_bitstream.py` or `tests/test_e2e.py`. Round-trip property tests
(forward → reverse → forward must reproduce the same entropy hex) are
especially valuable.

## Adding a Morse locale

The repository already ships:

| File | Locale | Standard |
|------|--------|----------|
| `examples/japanese.txt` | `jp` | ITU-R M.1677-1 (Wabun) + JARL |
| `examples/german.txt`  | `en` (layer) | ITU-R M.1677-1 |
| `examples/french.txt`  | `en` (layer) | ITU-R M.1677-1 |
| `examples/spanish.txt` | `en` (layer) | ITU-R M.1677-1 |

To add another:

1. Create `examples/<locale>.txt` following the format documented in the
   README (`# locale: <code>` header, then `<char> <whitespace> <morse>`
   lines). Cite the standard you used in a top comment.
2. If the file defines a *new* alphabet (e.g. Greek, Arabic, Hebrew), give
   it its own `locale:` code. If it just adds accented letters to an
   existing alphabet (e.g. Polish over Latin), use that base locale's
   code so the entries *layer onto* the built-in table.
3. Add a row in `tests/test_morse_tables.py` to cover at least one
   round-trip through the new file.
4. Add a short paragraph to the README's *Custom Morse tables* section
   (and the Russian README) — at minimum: standard cited, characters
   added, any caveats.
5. **Important:** the tool currently assumes that for every bit there is a
   1-bit letter that decodes it (`e`/`т` cover `0`/`1`). If your locale
   does not have 1-bit codes, the `bits_to_text` fallback chain
   (letters → digits → punctuation) must still cover both `0` and `1` at
   some length; verify with a round-trip test before submitting.

## Code style

- Python 3.11+ syntax is fine (match statements, type unions with `|`).
- Type hints are encouraged on public functions.
- No new runtime dependencies unless absolutely necessary. The current
  runtime footprint is `prompt_toolkit` only, and we'd like to keep it
  that way.
- Keep modules small and single-purpose; mirror the existing layout
  (`morse.py` for tables, `bitstream.py` for bit math, `bip39.py` for
  wordlist/mnemonic logic, `reverse.py` for word entry, `tui*.py` for UI).

## Commit messages

Imperative present tense, lowercase first letter, no trailing period for
the subject; wrap the body at ~72 chars. One logical change per commit;
keep refactors and behavioural changes in separate commits when possible.

Examples from the existing history:

```
Add --group-size and --per-line for reverse output formatting + CI
Make demo flow inline-realistic: TUI redraws in place, output appends below
Add iroha terminal demo (animated SVG + static PNG) to READMEs
```

## Pull request process

1. Fork the repo and create a topic branch off `master`:
   `feature/<short-name>` or `fix/<short-name>`.
2. Run `pytest` locally — it must pass with coverage ≥ 85%.
3. Update the README (and `README.ru.md`) for any user-visible change.
4. Add an entry to `CHANGELOG.md` under `[Unreleased]`.
5. Open the PR against `master`. Fill in the PR template.
6. CI (`.github/workflows/tests.yml`) will run pytest on push and PR.
   PRs must be green before review.

I usually reply within a few days. If a PR sits without feedback for a
week, feel free to ping it.

## Security-sensitive contributions

This is a tool that handles material directly tied to wallet seeds. Some
contribution categories require extra care:

- **Do not** paste real mnemonics, real entropy, or real wallet addresses
  in issues, PRs, screenshots, or test fixtures. Use the iroha vectors
  already in the repo, the Trezor public test vectors, or freshly
  generated throwaway phrases.
- **Do not** propose changes that introduce network calls, telemetry,
  clipboard writes, disk persistence of entropy, or randomness injection.
  These are intentional non-features (see the *Security notes* section
  of the README).
- For anything that touches `bitstream.py`, `bip39.py`, `morse.py`, or
  `reverse.py`, please include a round-trip test.
- If you find a security vulnerability, **do not open a public issue.**
  See [SECURITY.md](SECURITY.md) for the private reporting channel.

## License

By contributing, you agree that your contributions will be licensed under
the MIT License of this project (see `LICENSE.md`).
