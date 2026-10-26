"""Best-effort normaliser for MatCalc TDB files (experimental, not science).

Removes only vendor additions; never invents thermodynamic data. A file that
still fails to load is reported as failed, never silently patched.
"""
import pathlib
import re

DROP = ('REFERENCE_ELEMENT', 'ADD_COMPOSITION_SET', 'ATTACH_CONTRIBUTION',
        'DATABASE_INFO', 'ASSESSED_SYSTEMS', 'VERSION_DATE',
        'TEMPERATURE_LIMITS', 'DEFINE_SYSTEM_DEFAULT', 'DEFAULT_COMMAND',
        'LIST_OF_REFERENCES', 'CONST')
REF_TAG = re.compile(r'\s+N\s+REF:\S+')
PHASE_PROSE = re.compile(r'>\s*[^>]*>>', re.S)


def decode(raw: bytes) -> str:
    for codec in ('utf-8', 'cp1252'):
        try:
            return raw.decode(codec)
        except UnicodeDecodeError:
            pass
    return raw.decode('latin-1')


def normalise(text: str) -> str:
    lines = []
    for line in text.splitlines():
        token = line.strip().split(' ')[0].upper() if line.strip() else ''
        if token in DROP:
            continue
        lines.append(line)
    commands = []
    for command in '\n'.join(lines).split('!'):
        if not command.strip() or 'HMVA' in command.upper():
            continue
        command = REF_TAG.sub('', command).replace('%', '')
        head = command.strip().upper()
        if head.startswith('TYPE_DEF '):
            command = command.replace('TYPE_DEF ', 'TYPE_DEFINITION ', 1)
        elif head.startswith('FUN '):
            command = command.replace('FUN ', 'FUNCTION ', 1)
        elif head.startswith('PARA '):
            command = command.replace('PARA ', 'PARAMETER ', 1)
        if '>' in command and '>>' in command:
            command = PHASE_PROSE.sub('> >>', command)
        commands.append(command)
    return '\n!\n'.join(commands) + '\n!\n'


def convert(source: pathlib.Path, target: pathlib.Path) -> pathlib.Path:
    out = target / (source.stem + '.norm.tdb')
    out.write_text(normalise(decode(source.read_bytes())), encoding='utf-8')
    return out


if __name__ == '__main__':
    src = pathlib.Path('data/alloy_tdb')
    dst = pathlib.Path('data/alloy_tdb_normalized')
    dst.mkdir(exist_ok=True)
    for path in sorted(src.glob('*.tdb')):
        print(path.name, '->', convert(path, dst).name)
