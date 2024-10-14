import os
import re
import string
import shutil
from pathlib import Path

from .line_stripper import strip_lines
from .sugar_stripper import strip_classes, strip_imports
from .superclasses import strip_superclasses_leave, strip_superclasses

def patch_src(src):
    '''
    Patches source code
    '''
    lines = src.split("\n")
    patch_lines(lines)
    return "\n".join(lines)

def patch_lines(lines):
    strip_lines(lines)
    strip_classes(lines)
    strip_imports(lines)
    strip_superclasses_leave(lines)
    strip_superclasses(lines)

def load_file(src_path):
    """
    Loads file and strips symbols
    """
    with Path(src_path).open("r") as fp:
        data = fp.read()
    return patch_src(data)


TEXTCHARS = set(bytes(string.printable, 'ascii'))


def is_binary_file(src_path):
    with open(src_path,"rb") as f:
        printable = all(char in TEXTCHARS for char in f.read())
    return not printable


def copy_file_stripping(src,dst):
    """
    Copy file and replace its content by STRIP syntax
    """
    if is_binary_file(src):
        shutil.copy(src,dst)
        return

    data = load_file(src)

    with Path(dst).open("w") as fp:
        fp.write(data)