"""Regenerate the bip39-morse README demo (animated SVG + static PNG).

Pipeline (run from the project root):

    python3 docs/generate_demo.py

What this script produces, in order:

  1. docs/demo.cast       — asciinema v2 cast, keystroke-accurate:
                            each frame is re-rendered from a real BitStream
                            after pushing the next kana, so hex dump, bar,
                            and indicator state are bit-identical to the TUI.
  2. docs/demo-final.svg  — hand-crafted static SVG of the final terminal
                            state (used for the PNG fallback).
  3. docs/demo.svg        — animated SVG produced by termtosvg from #1,
                            with an injected DEMO watermark band.
  4. docs/demo-final.png  — static PNG rasterised from #2 via rsvg-convert.

External tools required for steps 3–4 (Homebrew on macOS):

    brew install librsvg
    pip install termtosvg

If those tools are missing the script still produces #1 and #2 and prints
a warning for the missing rendering steps — the .cast remains the source
of truth.

The phrase used is the IROHA — a 47-kana pangram from the Heian period
(9th-10th c.), enough for 186 bits of Morse entropy, past the 132 bits
needed for a 12-word BIP39 seed. It is famously public; the wallet
derived from it in this demo is therefore public too.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import time

from bip39_morse import morse
from bip39_morse.bip39 import indices_to_mnemonic, load_wordlist
from bip39_morse.bitstream import BitStream

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_JP = REPO_ROOT / 'examples' / 'japanese.txt'

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

ENTROPY_BITS = 128
TOTAL_BITS = 132
TERM_WIDTH = 100
TERM_HEIGHT = 12
BAR_WIDTH = 40

CMD = 'bip39-morse --morse-table examples/japanese.txt --length 12 --ascii'

# Timing budget (seconds) — total ~14s of animation.
T_PROMPT = 0.4
T_AFTER_CMD = 0.8
T_AFTER_INITIAL = 0.6
T_PER_KANA = 0.18
T_BEFORE_ENTER = 1.2
T_AFTER_OUTPUT = 2.5


def _indicator(ready: bool) -> str:
    """ANSI-coloured ASCII bullet (matches --ascii fallback)."""
    if ready:
        return '\x1b[32m●\x1b[0m'  # green ●
    return '\x1b[31m●\x1b[0m'  # red ●


def _bar(accumulated: int, ready: bool) -> str:
    ratio = min(accumulated, ENTROPY_BITS) / ENTROPY_BITS
    filled = int(ratio * BAR_WIDTH)
    empty = BAR_WIDTH - filled
    fill_char = '#'
    empty_char = '-'
    colour = '\x1b[32m' if ready else '\x1b[31m'
    return f'{colour}{fill_char * filled}\x1b[0m{empty_char * empty}'


def _frame(stream: BitStream) -> str:
    """Render the 4-line TUI to a clear-screen frame.

    \x1b[2J\x1b[H clears the screen and homes the cursor; agg renders
    each frame from this fresh state, so we don't have to bookkeep
    in-place updates.
    """
    ready = stream.is_ready
    counter_value = TOTAL_BITS if ready else stream.accumulated_bits
    buffer_text = stream.visual_buffer()
    hex_text = stream.hex_display()
    line_header = '\x1b[1;36mСлов: 12 (128 бит энтропии)\x1b[0m'
    line_hex = f'{_indicator(ready)} {hex_text}'
    line_bar = f'   {_bar(stream.accumulated_bits, ready)}  {counter_value}/{ENTROPY_BITS}'
    line_input = f'\x1b[1m›\x1b[0m  {buffer_text}\x1b[7m_\x1b[0m'
    return (
        '\x1b[2J\x1b[H'
        f'{line_header}\r\n'
        f'{line_hex}\r\n'
        f'{line_bar}\r\n'
        f'{line_input}\r\n'
    )


def build_events() -> list[list]:
    morse.reset_tables()
    morse.load_table_file(str(EXAMPLES_JP))

    wl = load_wordlist('english')
    stream = BitStream(entropy_bits=ENTROPY_BITS)

    events: list[list] = []
    t = 0.0

    # 1. Shell prompt + typed command + Enter.
    events.append([t, 'o', '\x1b[1;32m$\x1b[0m '])
    t += T_PROMPT
    # Type the command in one go (would otherwise be far too slow).
    events.append([t, 'o', CMD + '\r\n'])
    t += T_AFTER_CMD

    # 2. Initial TUI render.
    events.append([t, 'o', _frame(stream)])
    t += T_AFTER_INITIAL

    # 3. Type the iroha kana by kana.
    for ch in IROHA:
        stream.push(ch, morse.char_to_bits(ch))
        t += T_PER_KANA
        events.append([t, 'o', _frame(stream)])

    # 4. Brief pause on green state before Enter.
    t += T_BEFORE_ENTER

    # 5. Enter pressed → TUI exits, app prints normalized phrase + mnemonic.
    normalized = stream.normalized_input()
    mnemonic = indices_to_mnemonic(stream.indices(), wl)
    # Clear screen one last time, then print the two final lines, then
    # show a fresh shell prompt so the demo loops nicely.
    final = (
        '\x1b[2J\x1b[H'
        f'\x1b[1;32m$\x1b[0m {CMD}\r\n'
        f'{normalized}\r\n'
        f'{mnemonic}\r\n'
        '\r\n'
        '\x1b[1;32m$\x1b[0m \x1b[7m \x1b[0m\r\n'
    )
    events.append([t, 'o', final])
    t += T_AFTER_OUTPUT

    return events


def write_cast() -> None:
    events = build_events()
    header = {
        'version': 2,
        'width': TERM_WIDTH,
        'height': TERM_HEIGHT,
        'timestamp': int(time.time()),
        'env': {'SHELL': '/bin/bash', 'TERM': 'xterm-256color'},
        'title': 'bip39-morse demo — iroha (DEMO PHRASE, DO NOT USE)',
    }
    out = REPO_ROOT / 'docs' / 'demo.cast'
    with out.open('w', encoding='utf-8') as f:
        f.write(json.dumps(header, ensure_ascii=False) + '\n')
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + '\n')
    print(f'wrote {out} ({out.stat().st_size} bytes, {len(events)} events)')


def write_final_svg() -> None:
    """Hand-craft a static SVG showing only the final terminal state.
    rsvg-convert will rasterise it to PNG; agg only handles animated casts."""
    morse.reset_tables()
    morse.load_table_file(str(EXAMPLES_JP))
    wl = load_wordlist('english')
    stream = BitStream(entropy_bits=ENTROPY_BITS)
    for ch in IROHA:
        stream.push(ch, morse.char_to_bits(ch))
    normalized = stream.normalized_input()
    mnemonic = indices_to_mnemonic(stream.indices(), wl)

    # Layout constants tuned for a 100x12 terminal at 14px monospace.
    font_size = 14
    char_w = 8.4   # approximate monospace width at 14px
    line_h = 20
    pad = 18
    width = int(TERM_WIDTH * char_w + 2 * pad)
    height = 6 * line_h + 2 * pad + 36  # 5 content lines + watermark band

    lines = [
        ('green', f'$ {CMD}'),
        ('white', normalized),
        ('yellow', mnemonic),
        ('white', ''),
        ('green', '$'),
    ]
    colours = {
        'green': '#a6e22e',
        'yellow': '#e6db74',
        'white': '#f8f8f2',
        'red': '#f92672',
        'grey': '#75715e',
    }

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" '
        f'font-family="\'JetBrains Mono\', \'DejaVu Sans Mono\', Menlo, monospace" '
        f'font-size="{font_size}">',
        f'<rect width="100%" height="100%" fill="#272822"/>',
    ]
    y = pad + line_h
    for colour, text in lines:
        # Escape XML.
        text_xml = (
            text.replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
        )
        svg_lines.append(
            f'<text x="{pad}" y="{y}" fill="{colours[colour]}" '
            f'xml:space="preserve">{text_xml}</text>'
        )
        y += line_h

    # Watermark band along the bottom.
    wm_y = height - 14
    svg_lines.append(
        f'<rect x="0" y="{wm_y - 18}" width="{width}" height="32" '
        f'fill="#f92672" fill-opacity="0.18"/>'
    )
    svg_lines.append(
        f'<text x="{width // 2}" y="{wm_y}" fill="{colours["red"]}" '
        f'font-weight="bold" text-anchor="middle">'
        f'DEMO PHRASE — DO NOT USE FOR REAL FUNDS</text>'
    )
    svg_lines.append('</svg>')

    out = REPO_ROOT / 'docs' / 'demo-final.svg'
    out.write_text('\n'.join(svg_lines), encoding='utf-8')
    print(f'wrote {out} ({out.stat().st_size} bytes)')


WATERMARK_TEXT = 'DEMO PHRASE — DO NOT USE FOR REAL FUNDS'


def _inject_watermark(svg_path: pathlib.Path) -> None:
    """Add a red translucent band with the watermark text just before the
    outermost </svg>. Width is read from the viewBox so it adapts if the
    template changes."""
    content = svg_path.read_text(encoding='utf-8')
    # Pull width/height from the first viewBox we see (the outer SVG).
    import re
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
        f'fill="#f92672" fill-opacity="0.18"/>'
        f'<text x="{width / 2}" y="{text_y}" '
        f'font-family="\'JetBrains Mono\', \'DejaVu Sans Mono\', Menlo, monospace" '
        f'font-size="12" font-weight="bold" fill="#f92672" text-anchor="middle">'
        f'{WATERMARK_TEXT}</text></g>'
    )
    last = content.rfind('</svg>')
    out = content[:last] + band + content[last:]
    svg_path.write_text(out, encoding='utf-8')


def render_animated_svg() -> None:
    cast = REPO_ROOT / 'docs' / 'demo.cast'
    svg = REPO_ROOT / 'docs' / 'demo.svg'
    if shutil.which('termtosvg') is None:
        print('WARN: termtosvg not installed, skipping animated SVG (run: pip install termtosvg)')
        return
    subprocess.run(
        ['termtosvg', 'render', str(cast), str(svg), '-t', 'base16_default_dark'],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    _inject_watermark(svg)
    print(f'wrote {svg} ({svg.stat().st_size} bytes, with watermark)')


def render_final_png() -> None:
    final_svg = REPO_ROOT / 'docs' / 'demo-final.svg'
    final_png = REPO_ROOT / 'docs' / 'demo-final.png'
    if shutil.which('rsvg-convert') is None:
        print('WARN: rsvg-convert not installed, skipping PNG (run: brew install librsvg)')
        return
    subprocess.run(
        ['rsvg-convert', str(final_svg), '-o', str(final_png)],
        check=True,
    )
    print(f'wrote {final_png} ({final_png.stat().st_size} bytes)')


if __name__ == '__main__':
    write_cast()
    write_final_svg()
    render_animated_svg()
    render_final_png()
