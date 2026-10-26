"""Merge MatCalc's split PHASE/CONSTITUENT commands into standard TDB form.

Syntactic merge only: no data is invented. A phase without a CONSTITUENT is
left untouched and reported.
"""
import pathlib
import re

PHASE = re.compile(
    r'(?ms)^[ \t]*(?P<head>PHASE\s+(?P<name>\S+)\s+.*?)>(?P<mid>.*?)>>(?P<tail>.*)$'
)
CONST = re.compile(r'^\s*CONSTITUENT\s+(?P<name>\S+)\s*:(?P<body>.*):\s*$', re.S | re.I)


def merge(text: str):
    commands = [c for c in text.split('!') if c.strip()]
    constituents = {}
    for command in commands:
        match = CONST.match(command.strip())
        if match:
            constituents[match.group('name').strip('%').upper()] = match.group('body').strip()
    out, missing = [], []
    for command in commands:
        if CONST.match(command.strip()):
            continue
        match = PHASE.search(command)
        if match:
            name = match.group('name').strip('%').upper()
            body = constituents.get(name)
            if body is None:
                missing.append(name)
                out.append(command)
                continue
            head = match.group('head').replace('%', '')
            out.append(f'{head}> {body} >>{match.group("tail")}')
            continue
        out.append(command)
    return '\n!\n'.join(out) + '\n!\n', missing


def convert(source: pathlib.Path, target: pathlib.Path):
    text = source.read_bytes().decode('latin-1')
    merged, missing = merge(text)
    out = target / (source.stem + '.merged.tdb')
    out.write_text(merged, encoding='utf-8')
    return out, missing
