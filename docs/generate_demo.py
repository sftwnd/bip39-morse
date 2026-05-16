"""Regenerate the bip39-morse README demos (forward + reverse) as animated SVG + static PNG.

Pipeline (run from the project root):

    python3 docs/generate_demo.py

Produces, in order:

  1. docs/demo.cast               — forward asciinema v2 cast (iroha → mnemonic)
  2. docs/demo-final.svg          — static SVG of the forward final state
  3. docs/demo-reverse.cast       — reverse cast (mnemonic → Morse text)
  4. docs/demo-reverse-final.svg  — static SVG of the reverse final state
  5. docs/demo.svg                — animated SVG from #1, watermarked
  6. docs/demo-reverse.svg        — animated SVG from #3, watermarked
  7. docs/demo-final.png          — PNG rasterised from #2
  8. docs/demo-reverse-final.png  — PNG rasterised from #4

Both animated SVGs use a 5000 ms loop delay (1 s default + 4 s extra) so the
viewer can read the final state before the loop restarts.

External tools required for #5-#8 (macOS/Homebrew):

    brew install librsvg
    pip install termtosvg

If those tools are missing the script still produces #1-#4 and prints a warning.

Phrase: the IROHA — 47-kana Heian pangram, 186 bits, public.
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import time
from typing import Callable

from bip39_morse import morse
from bip39_morse.bip39 import indices_to_mnemonic, load_wordlist
from bip39_morse.bitstream import BitStream
from bip39_morse.reverse import WordEntry, format_grouped

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_JP = REPO_ROOT / 'examples' / 'japanese.txt'

# Shared constants
ENTROPY_BITS = 128
TOTAL_BITS = 132
TARGET_WORDS = 12
TERM_WIDTH = 100
TERM_HEIGHT = 14
BAR_WIDTH = 40
LOOP_DELAY_MS = 5000  # 1000ms default + 4s extra dwell on the final frame
WATERMARK_TEXT = 'DEMO PHRASE — DO NOT USE FOR REAL FUNDS'

# Forward demo
IROHA = (
    'イロハニホヘト'
    'チリヌルヲ'
    'ワカヨタレソ'
    'ツネナラム'
    'ウヰノオクヤマ'
    'ケフコエテ'
    'アサキユメミシ'
    'ヱヒモセス'
)
FORWARD_CMD = 'bip39-morse --morse-table examples/japanese.txt --length 12 --ascii'

# Reverse demo
REVERSE_MNEMONIC = 'file expect bid fly father whale portion fame doll social discover garlic'.split()
REVERSE_CMD = 'bip39-morse --reverse --length 12 --lang en --group-size 4 --per-line 4 --ascii'

# Timing
T_PROMPT = 0.4
T_AFTER_CMD = 0.8
T_AFTER_INITIAL = 0.6
T_PER_KANA = 0.18
T_PER_KEY = 0.15
T_INTERWORD = 0.30
T_BEFORE_ENTER = 1.2
T_AFTER_OUTPUT = 2.5


# ----------------------------------------------------------------------------
# Common rendering primitives
# ----------------------------------------------------------------------------

def _indicator(ready: bool) -> str:
    """ANSI-coloured ASCII bullet (matches --ascii fallback)."""
    return '\x1b[32m●\x1b[0m' if ready else '\x1b[31m●\x1b[0m'


def _bar(progress: int, target: int, ready: bool) -> str:
    """ASCII progress bar with red/green fill colour."""
    ratio = min(progress, target) / target if target else 0.0
    filled = int(ratio * BAR_WIDTH)
    empty = BAR_WIDTH - filled
    colour = '\x1b[32m' if ready else '\x1b[31m'
    return f'{colour}{"#" * filled}\x1b[0m{"-" * empty}'


def _hex_from_bits(bits: str) -> str:
    """Mirror reverse-mode hex layout: partial bytes pre-ready, then full
    entropy hex + ' │ ' + checksum bits once entropy_bits is reached."""
    if len(bits) >= ENTROPY_BITS:
        n_bytes = ENTROPY_BITS // 8
        val = int(bits[:ENTROPY_BITS], 2)
        hex_str = format(val, f'0{n_bytes * 2}X')
        groups = [hex_str[i:i + 4] for i in range(0, len(hex_str), 4)]
        entropy_hex = ' '.join(groups)
        cs = bits[ENTROPY_BITS:]
        return f'{entropy_hex} │ {cs}' if cs else entropy_hex
    n_complete = len(bits) // 8
    if n_complete == 0:
        return ''
    val = int(bits[:n_complete * 8], 2)
    hex_str = format(val, f'0{n_complete * 2}X')
    groups = [hex_str[i:i + 4] for i in range(0, len(hex_str), 4)]
    return ' '.join(groups)


# ----------------------------------------------------------------------------
# Forward demo
# ----------------------------------------------------------------------------

FORWARD_TUI_LINES = 4


def _forward_tui_body(stream: BitStream) -> list[str]:
    """The 4 TUI lines (without leading clear-screen or cursor-up)."""
    ready = stream.is_ready
    counter = TOTAL_BITS if ready else stream.accumulated_bits
    return [
        f'\x1b[1;36mСлов: {TARGET_WORDS} ({ENTROPY_BITS} бит энтропии)\x1b[0m',
        f'{_indicator(ready)} {stream.hex_display()}',
        f'   {_bar(stream.accumulated_bits, ENTROPY_BITS, ready)}  {counter}/{ENTROPY_BITS}',
        f'\x1b[1m›\x1b[0m  {stream.visual_buffer()}\x1b[7m_\x1b[0m',
    ]


def _initial_tui(lines: list[str]) -> str:
    """First-time render: just write the lines below the current cursor.
    Each line gets \x1b[K to wipe any residue, and \r\n to advance."""
    return ''.join(f'\x1b[K{line}\r\n' for line in lines)


def _redraw_tui(lines: list[str], n_lines: int) -> str:
    """In-place redraw: move cursor up n_lines, then rewrite each line.
    The command line above the TUI stays untouched."""
    return '\x1b[' + str(n_lines) + 'A' + ''.join(
        f'\r\x1b[K{line}\r\n' for line in lines
    )


def build_forward_events() -> list[list]:
    morse.reset_tables()
    morse.load_table_file(str(EXAMPLES_JP))
    stream = BitStream(entropy_bits=ENTROPY_BITS)

    events: list[list] = []
    t = 0.0
    # Shell prompt + typed command (one-shot). The command line stays at row 1
    # for the rest of the animation — never clear-screened away.
    events.append([t, 'o', '\x1b[1;32m$\x1b[0m '])
    t += T_PROMPT
    events.append([t, 'o', FORWARD_CMD + '\r\n'])
    t += T_AFTER_CMD
    # Initial empty TUI below the command line.
    events.append([t, 'o', _initial_tui(_forward_tui_body(stream))])
    t += T_AFTER_INITIAL
    # Type the iroha kana-by-kana; redraw TUI in place each time.
    for ch in IROHA:
        stream.push(ch, morse.char_to_bits(ch))
        t += T_PER_KANA
        events.append([t, 'o', _redraw_tui(_forward_tui_body(stream), FORWARD_TUI_LINES)])
    t += T_BEFORE_ENTER

    # On Enter, prompt_toolkit (inline mode) leaves the rendered TUI on
    # screen and returns control to the CLI which print()s the result on
    # the next free line. Match that: no clear-screen, just append below.
    wl = load_wordlist('english')
    final = (
        f'{stream.normalized_input()}\r\n'
        f'{indices_to_mnemonic(stream.indices(), wl)}\r\n'
        '\r\n'
        '\x1b[1;32m$\x1b[0m \x1b[7m \x1b[0m\r\n'
    )
    events.append([t, 'o', final])
    t += T_AFTER_OUTPUT
    return events


# ----------------------------------------------------------------------------
# Reverse demo
# ----------------------------------------------------------------------------

REVERSE_TUI_LINES = 6


def _reverse_tui_body(entry: WordEntry) -> list[str]:
    """The 6 TUI lines (without leading clear-screen or cursor-up)."""
    ready = entry.is_ready
    n_completed = len(entry.completed)
    bits = entry.bits()
    hex_text = _hex_from_bits(bits)

    decode_bits = bits[:ENTROPY_BITS] if len(bits) >= ENTROPY_BITS else bits
    morse_text = morse.bits_to_text(decode_bits, locale='en') if decode_bits else ''

    completed_str = ' '.join(entry.completed)
    if completed_str and entry.current:
        input_line = (
            f'\x1b[1m›\x1b[0m  '
            f'\x1b[2;32m{completed_str}\x1b[0m '
            f'{entry.current}\x1b[7m_\x1b[0m'
        )
    elif completed_str:
        input_line = (
            f'\x1b[1m›\x1b[0m  '
            f'\x1b[2;32m{completed_str}\x1b[0m\x1b[7m_\x1b[0m'
        )
    else:
        input_line = f'\x1b[1m›\x1b[0m  {entry.current}\x1b[7m_\x1b[0m'

    cand_line = ''
    if not ready:
        cands = entry.candidates(limit=8)
        if cands:
            cand_line = '   \x1b[2;37m' + '  '.join(cands) + '\x1b[0m'

    return [
        f'\x1b[1;36mСлов: {TARGET_WORDS} ({ENTROPY_BITS} бит энтропии)\x1b[0m',
        f'{_indicator(ready)} {hex_text}',
        f'   {_bar(n_completed, TARGET_WORDS, ready)}  {n_completed}/{TARGET_WORDS} слов',
        f'\x1b[1;34mМорзе:\x1b[0m {morse_text}',
        input_line,
        cand_line,
    ]


def build_reverse_events() -> list[list]:
    wl = load_wordlist('english')
    entry = WordEntry(wordlist=wl, target_words=TARGET_WORDS)

    events: list[list] = []
    t = 0.0
    events.append([t, 'o', '\x1b[1;32m$\x1b[0m '])
    t += T_PROMPT
    events.append([t, 'o', REVERSE_CMD + '\r\n'])
    t += T_AFTER_CMD
    events.append([t, 'o', _initial_tui(_reverse_tui_body(entry))])
    t += T_AFTER_INITIAL

    for word in REVERSE_MNEMONIC:
        prev_n = len(entry.completed)
        for ch in word:
            entry.push_char(ch)
            t += T_PER_KEY
            events.append([t, 'o', _redraw_tui(_reverse_tui_body(entry), REVERSE_TUI_LINES)])
            if len(entry.completed) > prev_n:
                break
        if len(entry.completed) == prev_n:
            entry.commit_current()
            t += T_PER_KEY
            events.append([t, 'o', _redraw_tui(_reverse_tui_body(entry), REVERSE_TUI_LINES)])
        t += T_INTERWORD

    t += T_BEFORE_ENTER

    decode_bits = entry.entropy_bits_str(ENTROPY_BITS)
    raw_text = morse.bits_to_text(decode_bits, locale='en')
    formatted = format_grouped(raw_text, group_size=4, per_line=4)

    # Append below the last TUI frame, no clear-screen.
    final = (
        '\r\n'.join(formatted.split('\n')) + '\r\n'
        '\r\n'
        '\x1b[1;32m$\x1b[0m \x1b[7m \x1b[0m\r\n'
    )
    events.append([t, 'o', final])
    t += T_AFTER_OUTPUT
    return events


# ----------------------------------------------------------------------------
# Cast writer
# ----------------------------------------------------------------------------

def _write_cast(events: list[list], path: pathlib.Path, title: str) -> None:
    header = {
        'version': 2,
        'width': TERM_WIDTH,
        'height': TERM_HEIGHT,
        'timestamp': int(time.time()),
        'env': {'SHELL': '/bin/bash', 'TERM': 'xterm-256color'},
        'title': title,
    }
    with path.open('w', encoding='utf-8') as f:
        f.write(json.dumps(header, ensure_ascii=False) + '\n')
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + '\n')
    print(f'wrote {path} ({path.stat().st_size} bytes, {len(events)} events)')


# ----------------------------------------------------------------------------
# Static final-frame SVG hand-crafters
# ----------------------------------------------------------------------------

COLOURS = {
    'green': '#a6e22e',
    'yellow': '#e6db74',
    'white': '#f8f8f2',
    'red': '#f92672',
    'blue': '#66d9ef',
    'grey': '#75715e',
}


Line = list[tuple[str, str]]  # list of (colour_key, text) segments


def _xml_escape(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _write_static_svg(path: pathlib.Path, lines: list[Line]) -> None:
    """Each entry of `lines` is a list of (colour_key, text) segments rendered
    on one row. An empty list = blank line."""
    font_size = 14
    char_w = 8.4
    line_h = 20
    pad = 18
    n_lines = max(len(lines), 5)
    width = int(TERM_WIDTH * char_w + 2 * pad)
    height = n_lines * line_h + 2 * pad + 36

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" '
        f'font-family="\'JetBrains Mono\', \'DejaVu Sans Mono\', Menlo, monospace" '
        f'font-size="{font_size}">',
        '<rect width="100%" height="100%" fill="#272822"/>',
    ]
    y = pad + line_h
    for segments in lines:
        if not segments:
            y += line_h
            continue
        tspans = ''.join(
            f'<tspan fill="{COLOURS[colour]}">{_xml_escape(text)}</tspan>'
            for colour, text in segments
        )
        parts.append(
            f'<text x="{pad}" y="{y}" xml:space="preserve">{tspans}</text>'
        )
        y += line_h
    wm_y = height - 14
    parts.append(
        f'<rect x="0" y="{wm_y - 18}" width="{width}" height="32" '
        f'fill="{COLOURS["red"]}" fill-opacity="0.18"/>'
    )
    parts.append(
        f'<text x="{width // 2}" y="{wm_y}" fill="{COLOURS["red"]}" '
        f'font-weight="bold" text-anchor="middle">{WATERMARK_TEXT}</text>'
    )
    parts.append('</svg>')
    path.write_text('\n'.join(parts), encoding='utf-8')
    print(f'wrote {path} ({path.stat().st_size} bytes)')


def write_forward_final_svg() -> None:
    """Static SVG mirroring the final on-screen state: command at the top,
    the green-state TUI, then the appended normalized phrase + mnemonic
    + new shell prompt."""
    morse.reset_tables()
    morse.load_table_file(str(EXAMPLES_JP))
    wl = load_wordlist('english')
    stream = BitStream(entropy_bits=ENTROPY_BITS)
    for ch in IROHA:
        stream.push(ch, morse.char_to_bits(ch))

    bar_full = '#' * BAR_WIDTH
    lines: list[Line] = [
        [('green', f'$ {FORWARD_CMD}')],
        [('blue', f'Слов: {TARGET_WORDS} ({ENTROPY_BITS} бит энтропии)')],
        [('green', '● '), ('white', stream.hex_display())],
        [('grey', f'   {bar_full}  {TOTAL_BITS}/{ENTROPY_BITS}')],
        [('white', f'›  {stream.visual_buffer()}')],
        [('white', stream.normalized_input())],
        [('yellow', indices_to_mnemonic(stream.indices(), wl))],
        [],  # blank
        [('green', '$')],
    ]
    _write_static_svg(REPO_ROOT / 'docs' / 'demo-final.svg', lines)


def write_reverse_final_svg() -> None:
    """Static SVG mirroring the final on-screen state: command at the top,
    the green-state reverse TUI (header / hex / bar / Морзе / input / empty
    candidates), then the appended formatted Morse text + new shell prompt."""
    wl = load_wordlist('english')
    entry = WordEntry(wordlist=wl, target_words=TARGET_WORDS)
    entry.paste_text(' '.join(REVERSE_MNEMONIC))
    decode_bits = entry.entropy_bits_str(ENTROPY_BITS)
    raw_text = morse.bits_to_text(decode_bits, locale='en')
    formatted = format_grouped(raw_text, group_size=4, per_line=4)
    bits = entry.bits()
    hex_text = _hex_from_bits(bits)
    bar_full = '#' * BAR_WIDTH
    completed_str = ' '.join(entry.completed)

    lines: list[Line] = [
        [('green', f'$ {REVERSE_CMD}')],
        [('blue', f'Слов: {TARGET_WORDS} ({ENTROPY_BITS} бит энтропии)')],
        [('green', '● '), ('white', hex_text)],
        [('grey', f'   {bar_full}  {TARGET_WORDS}/{TARGET_WORDS} слов')],
        [('blue', 'Морзе: '), ('white', raw_text)],
        [('white', '›  '), ('green', completed_str)],
        [],  # candidates line (empty when ready)
    ]
    for row in formatted.split('\n'):
        lines.append([('white', row)])
    lines.append([])
    lines.append([('green', '$')])
    _write_static_svg(REPO_ROOT / 'docs' / 'demo-reverse-final.svg', lines)


# ----------------------------------------------------------------------------
# Watermark injection (for termtosvg outputs)
# ----------------------------------------------------------------------------

def _inject_watermark(svg_path: pathlib.Path) -> None:
    content = svg_path.read_text(encoding='utf-8')
    m = re.search(r'viewBox="([\d.\- ]+)"', content)
    if not m:
        print(f'WARN: viewBox not found in {svg_path}, skipping watermark')
        return
    parts = m.group(1).split()
    width = float(parts[2])
    height = float(parts[3])
    band_h = 20
    band_y = height - band_h
    text_y = height - 6
    band = (
        f'<g pointer-events="none">'
        f'<rect x="0" y="{band_y}" width="{width}" height="{band_h}" '
        f'fill="{COLOURS["red"]}" fill-opacity="0.18"/>'
        f'<text x="{width / 2}" y="{text_y}" '
        f'font-family="\'JetBrains Mono\', \'DejaVu Sans Mono\', Menlo, monospace" '
        f'font-size="12" font-weight="bold" fill="{COLOURS["red"]}" text-anchor="middle">'
        f'{WATERMARK_TEXT}</text></g>'
    )
    last = content.rfind('</svg>')
    out = content[:last] + band + content[last:]
    svg_path.write_text(out, encoding='utf-8')


def render_animated_svg(cast_path: pathlib.Path, svg_path: pathlib.Path) -> None:
    if shutil.which('termtosvg') is None:
        print(f'WARN: termtosvg not installed, skipping {svg_path.name} (pip install termtosvg)')
        return
    subprocess.run(
        [
            'termtosvg', 'render', str(cast_path), str(svg_path),
            '-t', 'base16_default_dark',
            '-D', str(LOOP_DELAY_MS),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    _inject_watermark(svg_path)
    print(f'wrote {svg_path} ({svg_path.stat().st_size} bytes, loop-delay {LOOP_DELAY_MS}ms, watermarked)')


def render_final_png(static_svg: pathlib.Path, out_png: pathlib.Path) -> None:
    if shutil.which('rsvg-convert') is None:
        print(f'WARN: rsvg-convert not installed, skipping {out_png.name} (brew install librsvg)')
        return
    subprocess.run(
        ['rsvg-convert', str(static_svg), '-o', str(out_png)],
        check=True,
    )
    print(f'wrote {out_png} ({out_png.stat().st_size} bytes)')


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------

def main() -> None:
    docs = REPO_ROOT / 'docs'

    _write_cast(build_forward_events(), docs / 'demo.cast', 'bip39-morse demo — forward (iroha → mnemonic, DEMO)')
    write_forward_final_svg()

    _write_cast(build_reverse_events(), docs / 'demo-reverse.cast', 'bip39-morse demo — reverse (mnemonic → Morse text, DEMO)')
    write_reverse_final_svg()

    render_animated_svg(docs / 'demo.cast', docs / 'demo.svg')
    render_animated_svg(docs / 'demo-reverse.cast', docs / 'demo-reverse.svg')
    render_final_png(docs / 'demo-final.svg', docs / 'demo-final.png')
    render_final_png(docs / 'demo-reverse-final.svg', docs / 'demo-reverse-final.png')


if __name__ == '__main__':
    main()
