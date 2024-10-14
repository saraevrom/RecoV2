import re
import inspect


STRIPCLASS_TOKEN = re.compile(r"^\s*#\s*STRIP CLASS$\s*")
STRIPIMPORT_TOKEN = re.compile(r"^\s*#\s*STRIP IMPORTS?$\s*")

def get_class_end(lines: list[str], start_pos):
    for i in range(start_pos+1, len(lines)):
        line_strip = lines[i].rstrip()
        if line_strip and not line_strip.startswith("    "):
            return i
    return len(lines)


def strip_classes(lines:list[str]):
    i = 0
    while i<len(lines):
        if STRIPCLASS_TOKEN.match(lines[i]):
            i += 1
            if i < len(lines) and lines[i].startswith("class"):
                end = get_class_end(lines, i)
                lines[i-1] = ""
                for j in range(i,end):
                    lines.pop(i-1)
        else:
            i += 1

def strip_imports(lines:list[str]):
    i = 0
    while i < len(lines):
        if STRIPIMPORT_TOKEN.match(lines[i]):
            lines.pop(i)
            while i<len(lines) and (lines[i].startswith("from") or lines[i].startswith("import")):
                lines.pop(i)
        else:
            i += 1