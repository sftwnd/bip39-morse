import sys
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.styles import Style
from prompt_toolkit.output import create_output

from .morse import char_to_bits, forward_table, DIGITS, PUNCTUATION, _ascii_fold
from .bitstream import BitStream


_COMMON_DIACRITICS = (
    # Latin-1 supplement + Latin Extended-A covering most European
    # languages with diacritics. Used only when fold_diacritics=True
    # to expand the keystroke whitelist.
    'áàâäãåāăąæçćčďèéêëēĕęğħıíìîïīĭįĺľłńñňōŏőøœŕřśšşťțúùûüūŭůűųýŷÿźżž'
    'ÁÀÂÄÃÅĀĂĄÆÇĆČĎÈÉÊËĒĔĘĞĦÍÌÎÏĪĬĮĹĽŁŃÑŇŌŎŐØŒŔŘŚŠŞŤȚÚÙÛÜŪŬŮŰŲÝŶŸŹŻŽ'
)


def allowed_chars(fold_diacritics: bool = False) -> set[str]:
    """Set of accepted keystrokes: every char in the merged forward table
    (both cases) plus digits, punctuation, and space. When ``fold_diacritics``,
    additionally accept any common Latin diacritic whose ASCII fold is in
    the merged table — the keystroke handler will fold it on the fly via
    ``char_to_bits(ch, fold_diacritics=True)``."""
    letters = forward_table()
    base: set[str] = (
        set(letters.keys())
        | set(k.upper() for k in letters.keys())
        | set(DIGITS.keys())
        | set(PUNCTUATION.keys())
        | {' '}
    )
    if not fold_diacritics:
        return base
    for ch in _COMMON_DIACRITICS:
        if ch in base:
            continue
        folded = _ascii_fold(ch)
        if folded is None:
            continue
        if folded.lower() in letters or folded in DIGITS or folded in PUNCTUATION:
            base.add(ch)
    return base


def _make_indicator(ready: bool, use_ascii: bool) -> StyleAndTextTuples:
    if use_ascii:
        if ready:
            return [('class:green', '●')]
        return [('class:red', '●')]
    if ready:
        return [('', '🟢')]
    return [('', '🔴')]


def _make_progress_bar(accumulated: int, entropy_bits: int, total_bits: int, ready: bool, use_ascii: bool, width: int = 40) -> StyleAndTextTuples:
    ratio = min(accumulated, entropy_bits) / entropy_bits if entropy_bits else 0
    filled = int(ratio * width)
    empty = width - filled

    if use_ascii:
        fill_char = '#'
        empty_char = '-'
    else:
        fill_char = '█'
        empty_char = ' '

    bar_class = 'class:bar-green' if ready else 'class:bar-red'
    bg_class = 'class:bar-bg'

    result: StyleAndTextTuples = []
    result.append((bar_class, fill_char * filled))
    result.append((bg_class, empty_char * empty))

    if ready:
        counter = f'  {total_bits}/{entropy_bits}'
    else:
        counter = f'  {accumulated}/{entropy_bits}'
    result.append(('', counter))
    return result


def _clip_hex(hex_str: str, max_width: int) -> str:
    if len(hex_str) <= max_width:
        return hex_str
    return '…' + hex_str[-(max_width - 1):]


def run_tui(entropy_bits: int, wordlist: list[str], use_ascii: bool = False, fold_diacritics: bool = False) -> tuple[str, str] | None:
    stream = BitStream(entropy_bits=entropy_bits)
    result_holder: list[tuple[str, str]] = []
    hint_holder: list[str] = ['']
    word_count = (entropy_bits + entropy_bits // 32) // 11

    kb = KeyBindings()

    @kb.add('c-c')
    def _exit(event):
        event.app.exit(exception=KeyboardInterrupt)

    @kb.add('enter')
    def _enter(event):
        if not stream.is_ready:
            hint_holder[0] = f'нужно ещё {entropy_bits - stream.accumulated_bits} бит'
            event.app.invalidate()
            return
        from .bip39 import indices_to_mnemonic
        mnemonic = indices_to_mnemonic(stream.indices(), wordlist)
        norm = stream.normalized_input()
        result_holder.append((norm, mnemonic))
        event.app.exit()

    @kb.add('backspace')
    def _backspace(event):
        stream.pop()
        hint_holder[0] = ''
        event.app.invalidate()

    def _make_char_handler(ch):
        @kb.add(ch)
        def _handler(event):
            hint_holder[0] = ''
            bits = char_to_bits(ch, fold_diacritics=fold_diacritics)
            stream.push(ch, bits)
            event.app.invalidate()

    allowed = allowed_chars(fold_diacritics=fold_diacritics)
    for ch in allowed:
        _make_char_handler(ch)

    @kb.add(Keys.BracketedPaste)
    def _paste(event):
        skipped = 0
        for ch in event.data:
            if ch in allowed:
                stream.push(ch, char_to_bits(ch, fold_diacritics=fold_diacritics) if ch != ' ' else '')
            else:
                skipped += 1
        hint_holder[0] = f'пропущено {skipped} символ(а)' if skipped else ''
        event.app.invalidate()

    def get_hex_text() -> StyleAndTextTuples:
        ready = stream.is_ready
        indicator = _make_indicator(ready, use_ascii)

        hex_str = stream.hex_display()
        try:
            term_width = create_output().get_size().columns
        except Exception:
            term_width = 80
        # indicator takes ~2-3 chars + space
        max_hex = term_width - 4
        if hex_str:
            hex_str = _clip_hex(hex_str, max_hex)

        result: StyleAndTextTuples = indicator + [('', ' '), ('', hex_str), ('', '\n')]
        return result

    def get_bar_text() -> StyleAndTextTuples:
        ready = stream.is_ready
        total_bits = entropy_bits + (entropy_bits // 32)
        try:
            term_width = create_output().get_size().columns
        except Exception:
            term_width = 80
        bar_width = max(10, term_width - 20)
        result = [('', '   ')]
        result += _make_progress_bar(stream.accumulated_bits, entropy_bits, total_bits, ready, use_ascii, bar_width)
        result += [('', '\n')]
        return result

    def get_input_text() -> StyleAndTextTuples:
        buf = stream.visual_buffer()
        hint = hint_holder[0]
        result: StyleAndTextTuples = [('class:prompt', '›  '), ('', buf), ('class:cursor', '_')]
        if hint:
            result += [('', f'\n   '), ('class:hint', hint)]
        return result

    def get_header_text() -> StyleAndTextTuples:
        return [('class:header', f'Слов: {word_count} ({entropy_bits} бит энтропии)'), ('', '\n')]

    header_window = Window(content=FormattedTextControl(get_header_text), height=1)
    hex_window = Window(content=FormattedTextControl(get_hex_text), height=1)
    bar_window = Window(content=FormattedTextControl(get_bar_text), height=1)
    input_window = Window(content=FormattedTextControl(get_input_text), height=2)

    layout = Layout(HSplit([header_window, hex_window, bar_window, input_window]))

    style = Style.from_dict({
        'red': 'fg:ansired',
        'green': 'fg:ansigreen',
        'bar-red': 'bg:ansired fg:ansired',
        'bar-green': 'bg:ansigreen fg:ansigreen',
        'bar-bg': 'bg:ansiwhite fg:ansiwhite',
        'prompt': 'bold',
        'cursor': 'reverse',
        'hint': 'fg:ansiyellow',
        'header': 'bold fg:ansicyan',
    })

    app: Application = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
    )

    try:
        app.run()
    except KeyboardInterrupt:
        sys.exit(130)

    if result_holder:
        return result_holder[0]
    return None
