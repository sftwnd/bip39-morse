import sys
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.styles import Style
from prompt_toolkit.output import create_output

from .morse import bits_to_text
from .reverse import WordEntry


def _entry_chars(wordlist: list[str]) -> set[str]:
    chars: set[str] = set()
    for w in wordlist:
        for ch in w:
            chars.add(ch)
    return chars


def _make_indicator(ready: bool, use_ascii: bool) -> StyleAndTextTuples:
    if use_ascii:
        return [('class:green' if ready else 'class:red', '●')]
    return [('', '🟢' if ready else '🔴')]


def _make_progress_bar(done: int, total: int, ready: bool, use_ascii: bool, width: int = 40) -> StyleAndTextTuples:
    ratio = min(done, total) / total if total else 0
    filled = int(ratio * width)
    empty = width - filled
    fill_char = '#' if use_ascii else '█'
    empty_char = '-' if use_ascii else ' '
    bar_class = 'class:bar-green' if ready else 'class:bar-red'
    bg_class = 'class:bar-bg'
    return [
        (bar_class, fill_char * filled),
        (bg_class, empty_char * empty),
        ('', f'  {done}/{total} слов'),
    ]


def _clip(text: str, max_width: int) -> str:
    if len(text) <= max_width:
        return text
    return '…' + text[-(max_width - 1):]


def _hex_display(bits: str, entropy_bits: int) -> str:
    """Hex dump matching forward-mode style. Below entropy threshold, shows
    grouped hex of completed bytes only. At/above threshold, shows the
    entropy hex followed by the user-supplied checksum bits."""
    if len(bits) >= entropy_bits and entropy_bits > 0:
        n_bytes = entropy_bits // 8
        val = int(bits[:entropy_bits], 2)
        hex_str = format(val, f'0{n_bytes * 2}X')
        groups = [hex_str[i:i + 4] for i in range(0, len(hex_str), 4)]
        entropy_hex = ' '.join(groups)
        cs_bits = bits[entropy_bits:]
        return f'{entropy_hex} │ {cs_bits}' if cs_bits else entropy_hex
    n_complete = len(bits) // 8
    if n_complete == 0:
        return ''
    bits_complete = bits[:n_complete * 8]
    val = int(bits_complete, 2)
    hex_str = format(val, f'0{n_complete * 2}X')
    groups = [hex_str[i:i + 4] for i in range(0, len(hex_str), 4)]
    return ' '.join(groups)


def run_reverse_tui(
    entropy_bits: int,
    wordlist: list[str],
    locale: str,
    use_ascii: bool = False,
) -> str | None:
    target_words = (entropy_bits + entropy_bits // 32) // 11
    entry = WordEntry(wordlist=wordlist, target_words=target_words)
    allowed = _entry_chars(wordlist)
    hint_holder: list[str] = ['']
    result_holder: list[str] = []

    kb = KeyBindings()

    @kb.add('c-c')
    def _exit(event):
        event.app.exit(exception=KeyboardInterrupt)

    @kb.add('enter')
    def _enter(event):
        # If the current input is an exact wordlist word but auto-completion
        # did not fire (because it is also a prefix of longer words),
        # let Enter commit it explicitly.
        if entry.commit_current():
            hint_holder[0] = ''
            event.app.invalidate()
            return
        if not entry.is_ready:
            hint_holder[0] = f'нужно ещё {target_words - len(entry.completed)} слов(а)'
            event.app.invalidate()
            return
        text = bits_to_text(entry.entropy_bits_str(entropy_bits), locale=locale)
        result_holder.append(text)
        event.app.exit()

    def _try_commit(event):
        if entry.commit_current():
            hint_holder[0] = ''
        else:
            hint_holder[0] = f'{entry.current!r} не является словом списка' if entry.current else ''
        event.app.invalidate()

    @kb.add(' ')
    def _space(event):
        _try_commit(event)

    @kb.add('tab')
    def _tab(event):
        _try_commit(event)

    @kb.add('backspace')
    def _backspace(event):
        entry.pop()
        hint_holder[0] = ''
        event.app.invalidate()

    @kb.add(Keys.BracketedPaste)
    def _paste(event):
        committed, failed = entry.paste_text(event.data)
        if failed is not None:
            hint_holder[0] = f'не удалось распознать {failed!r} (пропущено)'
        elif committed:
            hint_holder[0] = ''
        event.app.invalidate()

    def _make_char_handler(ch: str):
        @kb.add(ch)
        def _handler(event):
            status = entry.push_char(ch)
            if status == 'rejected':
                hint_holder[0] = f'нет слов с префиксом {entry.current + ch!r}'
            else:
                hint_holder[0] = ''
            event.app.invalidate()

    for ch in allowed:
        _make_char_handler(ch)

    def get_header_text() -> StyleAndTextTuples:
        return [('class:header', f'Слов: {target_words} ({entropy_bits} бит энтропии)'), ('', '\n')]

    def get_hex_text() -> StyleAndTextTuples:
        ready = entry.is_ready
        indicator = _make_indicator(ready, use_ascii)
        hex_str = _hex_display(entry.bits(), entropy_bits)
        try:
            term_width = create_output().get_size().columns
        except Exception:
            term_width = 80
        if hex_str:
            hex_str = _clip(hex_str, term_width - 4)
        return indicator + [('', ' '), ('', hex_str), ('', '\n')]

    def get_morse_text() -> StyleAndTextTuples:
        bits = entry.entropy_bits_str(entropy_bits)
        text = bits_to_text(bits, locale=locale) if bits else ''
        try:
            term_width = create_output().get_size().columns
        except Exception:
            term_width = 80
        text = _clip(text, max(10, term_width - 8))
        return [('class:morse', 'Морзе: '), ('', text), ('', '\n')]

    def get_bar_text() -> StyleAndTextTuples:
        ready = entry.is_ready
        try:
            term_width = create_output().get_size().columns
        except Exception:
            term_width = 80
        bar_width = max(10, term_width - 20)
        result: StyleAndTextTuples = [('', '   ')]
        result += _make_progress_bar(len(entry.completed), target_words, ready, use_ascii, bar_width)
        result += [('', '\n')]
        return result

    def get_input_text() -> StyleAndTextTuples:
        last_word = entry.completed[-1] if entry.completed else ''
        result: StyleAndTextTuples = [('class:prompt', '›  ')]
        if last_word and not entry.current:
            result += [('class:done', last_word + ' ')]
        result += [('', entry.current), ('class:cursor', '_')]
        if hint_holder[0]:
            result += [('', '\n   '), ('class:hint', hint_holder[0])]
        return result

    def get_candidates_text() -> StyleAndTextTuples:
        if entry.is_ready:
            return [('', '')]
        cands = entry.candidates(limit=8)
        if not cands:
            return [('', '')]
        return [('class:cand', '   ' + '  '.join(cands))]

    header_window = Window(content=FormattedTextControl(get_header_text), height=1)
    hex_window = Window(content=FormattedTextControl(get_hex_text), height=1)
    bar_window = Window(content=FormattedTextControl(get_bar_text), height=1)
    morse_window = Window(content=FormattedTextControl(get_morse_text), height=1)
    input_window = Window(content=FormattedTextControl(get_input_text), height=2)
    cand_window = Window(content=FormattedTextControl(get_candidates_text), height=1)

    layout = Layout(HSplit([header_window, hex_window, bar_window, morse_window, input_window, cand_window]))

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
        'morse': 'fg:ansibrightblue',
        'done': 'fg:ansigreen',
        'cand': 'fg:ansibrightblack',
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
