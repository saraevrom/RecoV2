import re

"""
Let's make some markers for reducing some symbols by some comments
Syntax will be like:

Variant 1:
|#STRIP
|<code to strip>
|#REPLACE
|#Here goes commented code
|#For replacement
|#END

Variant 2:
|#STRIP
|<code to strip>
|#END

Variant 3
|# STRIP
|<line to strip>
"""


STRIP_TOKEN = re.compile(r"^\s*#\s*STRIP\s*$")
REPLACE_TOKEN = re.compile(r"^\s*#\s*REPLACE\s*$")
END_TOKEN = re.compile(r"^\s*#\s*END\s*$")

def strip_lines(lines:list):
    i = 0
    state = ()
    while state is not None:
        match state:
            case ():
                if i>=len(lines):
                    state = None
                elif STRIP_TOKEN.match(lines[i]):
                    state = (i,)
                    i += 1
                else:
                    i += 1
            case (start,):
                if i >= len(lines) or STRIP_TOKEN.match(lines[i]):
                    for j in range(2):
                        lines.pop(start)
                    i = start
                    state = ()
                elif REPLACE_TOKEN.match(lines[i]):
                    state = (start,i)
                    i += 1
                elif END_TOKEN.match(lines[i]):
                    for j in range(start,i+1):
                        lines.pop(start) # There is offset appearing
                    state = ()
                    i = start
                else:
                    i += 1
            case (start,repl_end):
                if END_TOKEN.match(lines[i]):
                    repl_ok = True
                    for j in range(repl_end+1,i):
                        if not lines[j].startswith("# "):
                            repl_ok = False
                    if repl_ok:
                        for j in range(repl_end + 1, i ):
                            lines[j] = lines[j][2:]  # Uncomment
                        lines.pop(i)
                        for j in range(start,repl_end+1):
                            lines.pop(start)         # There is offset appearing
                        i = start
                        state = ()
                    else:
                        i += 1
                        state = ()
                elif i >= len(lines):
                    i = repl_end+1
                    state = ()
                else:
                    i += 1