# bip39-morse

*[Русская версия](README.ru.md)*

Interactive TUI that converts a Morse-typed phrase into a BIP39 mnemonic (and back), with pluggable per-locale Morse alphabets.

## Security warning — read this before generating anything real

Generating a real BIP39 phrase on a general-purpose computer is **inherently risky** and is done entirely at your own risk. Only proceed on a machine you are completely certain is **not** under an attacker's control — and even then, treat the result as compromised the moment anything unexpected happens during the session.

- **Windows 11 is strongly discouraged** as the host OS. Telemetry, Recall snapshots, OneDrive auto-sync, the clipboard history service, screen-capture pipelines, third-party update agents, and the long tail of unaudited drivers all make it a poor environment for handling seed entropy. The same caution applies, in varying degrees, to any consumer OS that you have not personally hardened.
- **Recommended setup.** Boot a clean live OS (e.g. Tails or a minimal Linux ISO) from a USB stick on a known-trusted machine. Disconnect the network. Run the tool. Never persist the phrase, the mnemonic, or any intermediate hex to a disk or cloud drive — type it directly into the offline cold-storage device that will hold the seed.
- **Round-trip self-check before you trust the output.** This tool is fully deterministic and reversible — verify that yourself, on the spot:
  1. Run forward mode on your typed phrase → note the **entropy hex** (the part to the left of `│` on the green-indicator line) and the resulting mnemonic.
  2. Run `--reverse` with the same `--length`/`--wordlist`, enter the mnemonic → it prints the decoded "reverse trash" text.
  3. Run forward mode again on that reverse-trash text → it must produce the **same entropy hex** as step 1 (and hence the same mnemonic).

  If the hex in steps 1 and 3 does not match exactly, **do not use the mnemonic** — something in the environment is interfering with the tool.
- **Wipe traces.** After verification, shut down the live OS cleanly so swap and tmpfs are gone with it. Do not screenshot the TUI, do not paste anything into a chat or a note-taking app, and remember that anything you typed may still be in scrollback until the terminal process exits.

## How it works

The script is a bridge between two representations of the same entropy:

- a **phrase in Morse code** (a sequence of characters whose International Morse codes, written as `0`/`1` for `.`/`-`, concatenate into a bit string), and
- a **BIP39 mnemonic** (a list of 12/18/24 words drawn from a 2048-word dictionary, where each word encodes 11 bits of a longer string formed by `entropy ‖ SHA256(entropy)`).

It runs as an interactive TUI (`prompt_toolkit`) and has two opposite directions:

### Morse alphabet

`bip39_morse/morse.py` keeps three kinds of lookup data:

- **Letters** are organised as a **layered registry**: an ordered list of `(locale, mapping)` pairs. Two layers are built in — `en` (`LATIN`, 26 codes) and `ru` (`CYRILLIC`, 33 codes incl. `ё`, sharing the code of `е`). Extra layers can be appended at runtime via `--morse-table PATH` (see below). When two layers define the same character, the later layer wins.
- **Digits** `0–9` — all 5-symbol ITU codes (shared across all locales).
- **Punctuation** — `.`, `,`, `-`, `!`, `?`, `:` (5–6 symbols, shared).

For any character, `char_to_bits(ch)` looks up its Morse code in the merged forward map (every loaded layer collapsed into one `char → morse` dict) and rewrites it as a bit string (`.` → `0`, `-` → `1`). Space yields the empty bit string — it acts only as a visual word separator and contributes no entropy.

Reverse decoding (`bits_to_text(bits, locale=...)`) reads only the layers tagged with the chosen locale, so the same bit pattern can decode into different alphabets depending on which locale you ask for.

A key property exploited later for the built-in en/ru locales: both `e`/`е` map to the single bit `0` and both `t`/`т` map to the single bit `1`, so every possible bit string is decodable into letters without padding. Custom locales need not satisfy this; the decoder falls back to digits, then punctuation, if no letter matches at any length.

#### Custom Morse tables

Pass `--morse-table PATH` (repeatable) to extend or override the built-ins from a file. Format:

```
# locale: jp
# name: Japanese Wabun code (optional)
# Comments and blank lines are ignored.
# Lines: <single-char> <whitespace> <morse>      (morse uses '.' and '-')
イ .-
ロ .-.-
ハ -...
...
```

- The `# locale: <code>` header is required and assigns the layer to a locale (any short string — `jp`, `de`, `es`, …).
- Each subsequent definition of the same character — within the file or across files — overrides earlier ones (including the built-in `en`/`ru` layers, so you can patch a single letter if needed).
- Letters are stored case-insensitively (`forward_table()` keys are lowercased; lookup also lowercases).

A ready example lives at [`examples/japanese.txt`](examples/japanese.txt) — the standard 48-katakana Wabun code plus dakuten/handakuten/long-vowel marks, transcribed from [ITU-R M.1677-1](https://www.itu.int/rec/R-REC-M.1677/en) and the JARL Wabun standard. Load it with:

```bash
python -m bip39_morse --morse-table examples/japanese.txt --reverse --lang jp
```

Then reverse-mode output will be rendered in katakana. (The same bit pattern `01` decodes as `A` for `--lang en`, `А` for `--lang ru`, and `イ` for `--lang jp` — `bits_to_text` only reads layers tagged with the requested locale.)

#### Latin accent extensions (German / French / Spanish)

Several Western-European languages don't need a separate alphabet — they just add a handful of accented letters on top of A–Z. The repository ships three ITU-R M.1677-1 extensions tagged with `locale: en`, so they **layer onto the built-in English alphabet** instead of creating a new locale:

| File | Adds |
|------|------|
| [`examples/german.txt`](examples/german.txt) | `Ä`, `Ö`, `Ü`, `ß` |
| [`examples/french.txt`](examples/french.txt) | `À`, `Ç`, `É`, `È` |
| [`examples/spanish.txt`](examples/spanish.txt) | `Ñ`, `Ü` |

You can load any combination — they don't conflict with each other (the few overlapping letters, e.g. `Ü` in both German and Spanish, share the same ITU code).

##### Example: French session

```bash
python -m bip39_morse --morse-table examples/french.txt --length 12
```

After this, the forward-mode TUI accepts `à / ç / é / è` (both cases) alongside the regular A–Z. Type a French passphrase:

```
Слов: 12 (128 бит энтропии)
🟢 A3F2 B1C4 0911 7E2D 5C8A 6F03 D4E1 9B25 │ 1100
   ████████████████████████████████████████  132/128
›  Le café à Paris est très bon_
```

Press `Enter`:

```
LE CAFÉ À PARIS EST TRÈS BON
island legal forest above ... (12 words)
```

Because the file extends `locale: en`, no `--lang` flag is needed — `--reverse` still defaults to `en`, and the decoder may emit `Ä` / `É` / etc. where their ITU codes don't collide with a base Latin letter.

**Caveat.** ITU-R M.1677-1 defines official codes only for the accented letters listed in each example file. Other diacritics (e.g. `Â`, `Ê`, `Î`, `Ô`, `Ï`, `Ë`, `Ù`, `Û` in French; `Á`, `Í`, `Ó`, `Ú` in Spanish) have no standard Morse code — radio operators traditionally drop the accent. If your convention requires them, add the rows yourself; later entries override earlier ones in the merged forward table.

### Bit math

For `N` words the BIP39 layout is:

```
total_bits = 11 · N
entropy_bits = total_bits · 32 / 33   (= 128, 192, or 256)
checksum_bits = entropy_bits / 32     (= 4, 6, or 8)
```

The TUI accepts a `--length` of 12/18/24 and derives `entropy_bits` from this table.

### Forward mode — phrase → mnemonic

Implemented in `bitstream.py` + `tui.py`. The data flow on each keystroke:

1. The character is mapped to its Morse bit string via `char_to_bits`.
2. `BitStream.push(char, bits)` appends the bits to an internal accumulator and the displayed character to a visual buffer. Each push is also recorded on a stack so `Backspace` can roll the exact same bits back off.
3. While `accumulated_bits < entropy_bits`, the hex view shows the completed bytes of the accumulator (groups of 4 hex chars). The indicator is red.
4. As soon as `accumulated_bits ≥ entropy_bits`, the first `entropy_bits` bits are treated as the entropy; `SHA-256(entropy)` is computed and its top `checksum_bits` bits are appended. The hex view switches to `entropy_hex │ checksum_bits` and the indicator turns green. Extra characters typed after that point still appear in the visual buffer and contribute to normalization, but they are ignored for mnemonic derivation.
5. On `Enter` (only while green) the `entropy ‖ checksum` string is split into 11-bit groups, each group indexes the wordlist, and the program prints two lines: the normalized phrase (uppercased, whitespace collapsed to single spaces) and the BIP39 mnemonic.

Pasting via Cmd/Ctrl+V iterates the pasted text and feeds each allowed character through the same `push` pipeline; unsupported characters are skipped with a hint.

### Reverse mode — words → Morse text

Implemented in `reverse.py` + `tui_reverse.py`. Here the user types words from the BIP39 wordlist and the script renders the resulting bits as readable Morse text.

1. **Word entry** — `WordEntry.push_char` appends a character to the current partial word and checks how many wordlist entries still start with it:
   - 1 match → the word is auto-completed and committed (a space is implicit; the next char starts a new word).
   - 0 matches → the character is rejected.
   - 2+ matches → it stays in the buffer; up to 8 candidates are shown live as a hint.
   For words that are themselves a prefix of longer ones (e.g. `van` vs `vanish`) auto-complete cannot fire, so `Space`, `Tab`, and `Enter` call `commit_current()` to commit the exact typed word.

2. **Paste** — `WordEntry.paste_text(text)` splits the pasted string on any of space/tab/CR/LF, prepends the current partial buffer to the first token, then resolves each token as either an exact wordlist word (winning over prefix-of-others) or a unique prefix. It stops at the first ambiguous/unknown token.

3. **Bits** — once `N` words are committed, their 11-bit indices concatenate into the same `entropy ‖ checksum` layout that forward mode produces.

4. **Bits → text** — `bits_to_text(bits, locale)` walks the first `entropy_bits` bits left-to-right. At every position it considers all letter codes that prefix the remaining bits at any length 1..6, picks the **least-used letter so far** (tie-break: longest code, then alphabetical), and consumes that many bits. If no letter matches at any length, the algorithm falls back to digits, then punctuation. Because letters always match at length 1, the bit string is always exhausted exactly — no padding is needed and no backtracking can occur. The least-used rule spreads the output across letters: 128 zero bits become `HSIE HSIE … HSE` rather than a long run of `H`.

5. **Display & finalize** — the TUI shows the live Morse text, a hex dump (same format as forward mode, with the user-provided checksum after the `│` once all words are entered), a progress bar `N_completed / N_target`, and the red/green indicator. `Enter` while green prints the decoded Morse text.

### Round-trip

Forward and reverse are inverses with one caveat. If the user types a Morse phrase, derives a mnemonic, and then in reverse mode re-enters those words, the printed Morse text — fed back into forward mode — will reproduce **exactly the same entropy**, hence the same first `N−1` words. The last word may differ only when the original word set did not have a valid BIP39 checksum (forward mode always recomputes the checksum, so an inconsistent input is silently corrected). This is the standard BIP39 invariant, not a quirk of this tool.

## Installation

```bash
pip install -e ".[test]"
```

## Usage

```bash
python -m bip39_morse [--length {12|18|24}] [--wordlist english|russian|<path>] [--reverse] [--morse-table PATH ...] [--lang LOCALE] [--ascii]
```

Or via the installed entry point:

```bash
bip39-morse --length 12
```

### Options

| Flag | Description |
|------|-------------|
| `--length` | Number of mnemonic words: `12`, `18`, or `24`. Default: `24`. |
| `--wordlist` | Wordlist to use: `english` (default), `russian`, or a path to a custom 2048-word file. |
| `--reverse` | Reverse mode: type BIP39 words with autocompletion, render the resulting Morse-decoded text. |
| `--morse-table PATH` | Load an extra Morse alphabet from a file (see [Custom Morse tables](#custom-morse-tables)). Repeatable; later files override earlier ones (and the built-in tables) for any character defined more than once. |
| `--lang LOCALE` | Output Morse alphabet for `--reverse` (locale code: `en`, `ru`, or any locale registered via `--morse-table`, e.g. `jp`). Default: the locale of the last loaded `--morse-table` file if any; otherwise auto-detected from `--wordlist` (russian → ru, else en). |
| `--ascii` | Use ANSI-colored `●` instead of emoji indicators (for terminals without UTF-8 emoji support). |

## Forward mode (default)

Type a phrase → Morse bits → BIP39 mnemonic.

### Keys

| Key | Action |
|-----|--------|
| Latin/Cyrillic letters, digits `0-9`, `.`, `,`, `-`, `!`, `?`, `:`, `Space` | Add character to phrase |
| Paste (Cmd/Ctrl+V) | Bulk-insert text — unknown characters are skipped with a hint |
| `Backspace` | Remove last character and roll back its bits |
| `Enter` | Finalize and print mnemonic (only when indicator is green) |
| `Ctrl+C` | Exit without output (exit code 130) |

### Example session

```
Слов: 12 (128 бит энтропии)
🟢 A3F2 B1C4 0911 7E2D 5C8A 6F03 D4E1 9B25 │ 1100
   ████████████████████████████████████████  132/128
›  Привет, мир!_
```

After pressing `Enter`:

```
ПРИВЕТ, МИР!
island cat forest above ... (12 words)
```

## Reverse mode (`--reverse`)

Type BIP39 words (with prefix-autocomplete) → indices → bits → Morse-decoded text.

- As you type a word, up to 8 wordlist candidates are shown (the first 8 of the wordlist before you start typing).
- When a single candidate matches the prefix, the word is committed automatically and a space is appended.
- For words that are themselves prefixes of other words (e.g. `van` vs `vanish`), press **Space** or **Tab** (or **Enter**) to commit the typed word explicitly.
- **Paste** (Cmd/Ctrl+V) accepts a full mnemonic with any whitespace separators (space, tab, CR, LF). Each pasted token may be either a complete BIP39 word or a prefix that uniquely identifies one. The first pasted token is concatenated with any partial input already in the buffer. Paste stops on the first unresolvable (ambiguous or unknown) token, leaving everything before it committed.
- A hex dump of the accumulated bits is shown live, identical in style to forward mode (`entropy_hex │ checksum_bits` once all words are entered).
- The decoded Morse text is displayed live above the input.
- After the last word, the indicator turns green; press `Enter` to print the text.

Morse alphabet selection: explicit `--lang <locale>` takes precedence. If omitted, the default is the locale of the **last** loaded `--morse-table` file (so `--morse-table examples/japanese.txt` without `--lang` renders in katakana); if no extra tables were loaded, it falls back to auto-detection from `--wordlist` (russian ⇒ Cyrillic, else Latin). This lets you mix — e.g. enter a Russian mnemonic and render the Morse text in Latin alphabet, or in any custom locale you have loaded.

Decoding strategy: at each position, the algorithm picks the **least-used letter** so far (tie-break: longer code wins, then alphabetical). This rotates through letters instead of collapsing into long runs (e.g. 128 zero bits become `HSIE HSIE … HSE` rather than `HHHH…`). If no letter matches at any length, it falls back to digits, then punctuation. Since `e`/`е` and `t`/`т` cover the 1-bit cases, letters always match, so the output is letters-only and no backtracking is needed.

The text round-trips through forward mode: feeding it back reproduces the same first 23 words; the last word may differ if the original 24-word input did not have a valid BIP39 checksum (which is standard BIP39 behavior).

## Running tests

```bash
pytest
```

Coverage report is printed automatically. The minimum threshold is 85% for `morse`, `bitstream`, and `bip39` modules.

## Project structure

```
bip39_morse/
  __main__.py      entry point for python -m
  cli.py           argparse + main()
  morse.py         Morse tables (layered registry) + char↔bits converters
  bitstream.py     bit accumulator, hex display, backspace, checksum
  bip39.py         wordlist loading, entropy→mnemonic
  reverse.py       word-entry model with prefix-autocomplete
  tui.py           prompt_toolkit TUI (forward mode)
  tui_reverse.py   prompt_toolkit TUI (reverse mode)
  wordlists/
    english.txt    2048-word BIP39 English wordlist
    russian.txt    2048-word BIP39 Russian wordlist
examples/
  japanese.txt    Sample Wabun (Japanese) Morse table (locale: jp)
  german.txt      ITU-R M.1677-1 German accent extension (locale: en)
  french.txt      ITU-R M.1677-1 French accent extension (locale: en)
  spanish.txt     ITU-R M.1677-1 Spanish accent extension (locale: en)
tests/
  test_morse.py
  test_morse_tables.py
  test_bitstream.py
  test_bip39.py
  test_reverse.py
  test_e2e.py
  vectors/
    trezor_vectors.json   official Trezor test vectors
```

## Security notes

These are properties of the tool itself; see the [security warning at the top](#security-warning--read-this-before-generating-anything-real) for the much larger question of the environment you run it in.

- No entropy is saved to disk.
- No network calls at runtime.
- No randomness injected — entropy comes exclusively from your typed phrase.
- Do not share your phrase; it is the seed for your mnemonic.
