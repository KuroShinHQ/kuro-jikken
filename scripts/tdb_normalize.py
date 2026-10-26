"""Best-effort normaliser for vendor TDB files (experimental, not science).

Drops vendor commands, decodes legacy bytes, strips N REF tags and HMVA
parameters and expands the FUN/PARA abbreviations. It writes a copy; the
downloaded originals are never edited. If pycalphad still refuses a file, the
file stays unusable - the report says so instead of hiding it.
"""
import pathlib
import re

DROP = ('REFERENCE_ELEMENT', 'ADD_COMPOSITION_SET', 'ATTACH_CONTRIBUTION',
        'DATABASE_INFO', 'ASSESSED_SYSTEMS', 'VERSION_DATE',
        'TEMPERATURE_LIMITS', 'DEFINE_SYSTEM_DEFAULT', 'DEFAULT_COMMAND',
        'LIST_OF_REFERENCES')
REF = re.compile(r'\s+N\s+REF:\S+')


def normalise(text: str) -> str:
    lines = []
    for line in text.splitlines():
        token = line.strip().split(' ')[0].upper() if line.strip() else ''
        if token in DROP:
            continue
        lines.append(line)
    out = []
    for command in '\n'.join(lines).split('!'):
        if not command.strip() or 'HMVA' in command.upper():
            continue
        command = REF.sub('', command).replace('%', '')
        head = command.strip().upper()
        if head.startswith('PARA '):
            command = command.replace('PARA ', 'PARAMETER ', 1)
        elif head.startswith('FUN '):
            command = command.replace('FUN ', 'FUNCTION ', 1)
        out.append(command)
    return '\n!\n'.join(out) + '\n!\n'


def main() -> None:
    source = pathlib.Path('data/alloy_tdb')
    target = pathlib.Path('data/alloy_tdb_normalized')
    target.mkdir(exist_ok=True)
    for path in sorted(source.glob('*.tdb')):
        text = path.read_bytes().decode('latin-1')
        out = target / (path.stem + '.norm.tdb')
        out.write_text(normalise(text), encoding='utf-8')
        print(path.name, '->', out.name)


if __name__ == '__main__':
    main()
