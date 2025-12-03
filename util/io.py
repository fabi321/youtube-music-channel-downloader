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
        return open(os.devnull, "w")
    else:
        return sys.stderr


def always_gen(n: int, v):
    for i in range(n):
        yield v


def join_and_create(base: Path, added: str) -> Path:
    new_filename: str = sanitize_filename(added)
    if base.is_dir():
        for obj in base.iterdir():
            if obj.is_dir() and obj.name.lower() == new_filename.lower():
                return obj
    joined = base.joinpath(new_filename)
    joined.mkdir(parents=True, exist_ok=True)
    return joined
