import argparse
import sys

from . import morse
from .bip39 import load_wordlist
from .reverse import format_grouped
from .tui import run_tui
from .tui_reverse import run_reverse_tui


def _positive_int(value: str) -> int:
    iv = int(value)
    if iv < 1:
        raise argparse.ArgumentTypeError(f'must be >= 1, got {iv}')
    return iv

LENGTH_MAP = {
    12: 128,
    18: 192,
    24: 256,
}


def main():
    parser = argparse.ArgumentParser(
        prog='bip39-morse',
        description='Interactive TUI: type a phrase in Morse code to generate a BIP39 mnemonic, or reverse — type BIP39 words to render their Morse text.',
    )
    parser.add_argument(
        '--length',
        type=int,
        default=24,
        choices=[12, 18, 24],
        help='Number of mnemonic words: 12, 18, or 24 (default: 24)',
    )
    parser.add_argument(
        '--wordlist',
        default='english',
        help='Wordlist: "english" (default), "russian", or path to a custom file',
    )
    parser.add_argument(
        '--reverse',
        action='store_true',
        help='Reverse mode: type BIP39 words, render Morse text from their bits',
    )
    parser.add_argument(
        '--morse-table',
        action='append',
        default=[],
        metavar='PATH',
        help='Load an extra Morse alphabet from a file (repeatable). '
             'The file must declare its locale via a "# locale: <code>" header. '
             'Later files override earlier ones (and the built-in en/ru tables) '
             'for any character defined more than once.',
    )
    parser.add_argument(
        '--lang',
        default=None,
        metavar='LOCALE',
        help='Output Morse alphabet for --reverse (locale code, e.g. en, ru, jp). '
             'If omitted: defaults to the locale of the last loaded --morse-table '
             'file; otherwise auto-detected from --wordlist (russian → ru, else en).',
    )
    parser.add_argument(
        '--group-size',
        type=_positive_int,
        default=5,
        metavar='N',
        help='For --reverse output: split the printed Morse text into '
             'space-separated groups of N characters. Default: 5.',
    )
    parser.add_argument(
        '--per-line',
        type=_positive_int,
        default=None,
        metavar='N',
        help='For --reverse output: insert a newline after every N groups. '
             'If omitted, all groups are printed on a single line.',
    )
    parser.add_argument(
        '--ascii',
        action='store_true',
        help='Use ANSI-colored ASCII bullet instead of emoji indicators',
    )

    args = parser.parse_args()

    last_loaded: str | None = None
    for path in args.morse_table:
        try:
            last_loaded = morse.load_table_file(path)
        except (FileNotFoundError, ValueError) as exc:
            print(f'Error loading Morse table {path!r}: {exc}', file=sys.stderr)
            sys.exit(1)

    try:
        wordlist = load_wordlist(args.wordlist)
    except (FileNotFoundError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)

    entropy_bits = LENGTH_MAP[args.length]

    if args.reverse:
        if args.lang is not None:
            locale = args.lang.lower()
        elif last_loaded is not None:
            locale = last_loaded
        else:
            locale = 'ru' if args.wordlist == 'russian' else 'en'
        if locale not in morse.list_locales():
            print(
                f'Error: unknown locale {locale!r}. Available: '
                f'{", ".join(morse.list_locales())}',
                file=sys.stderr,
            )
            sys.exit(1)
        text = run_reverse_tui(
            entropy_bits=entropy_bits,
            wordlist=wordlist,
            locale=locale,
            use_ascii=args.ascii,
        )
        if text is not None:
            print(format_grouped(text, group_size=args.group_size, per_line=args.per_line))
        return

    result = run_tui(entropy_bits=entropy_bits, wordlist=wordlist, use_ascii=args.ascii)
    if result is not None:
        normalized, mnemonic = result
        print(normalized)
        print(mnemonic)
