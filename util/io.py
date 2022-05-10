import os
import sys
from pathlib import Path

from pathvalidate import sanitize_filename

from util import types


def bprint(*args, **kwargs):
    if not types.Options.background:
        print(*args, **kwargs)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def get_output_pipe():
    if types.Options().background:
        return open(os.devnull, 'w')
    else:
        return sys.stderr


def always_gen(n: int, v):
    for i in range(n):
        yield v


def join_and_create(base: Path, added: str) -> Path:
    joined = base.joinpath(sanitize_filename(added))
    try:
        joined.mkdir()
    except FileExistsError:
        pass
    return joined
