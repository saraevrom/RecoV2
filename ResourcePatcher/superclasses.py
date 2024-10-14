import re

STRIP_SUPERCLASSES_EXCEPT = re.compile(r"\s*#\s*STRIP\s*SUPERCLASSES\s*EXCEPT\s*(.*)")
STRIP_SUPERCLASSES = re.compile(r"\s*#\s*STRIP\s*SUPERCLASSES\s*(.*)")

CLASS_REGEX = re.compile(r"^class ([\w_]+)\(([\w_,\s]+)\):")

def strip_superclasses_leave(lines:list[str]):
    i = 0
    while i<len(lines)-1:
        mat1 = STRIP_SUPERCLASSES_EXCEPT.match(lines[i])
        if mat1:
            mat2 = CLASS_REGEX.match(lines[i+1])
            if mat2:
                superclasses_to_result = mat1.groups()[0].split(",")
                superclasses_to_result = set([item.strip() for item in superclasses_to_result])
                identifier, actual_superclasses = mat2.groups()
                actual_superclasses = actual_superclasses.split(",")
                actual_superclasses = set([item.strip() for item in actual_superclasses])
                result_superclasses = list(superclasses_to_result.intersection(actual_superclasses))
                if not result_superclasses:
                    result_superclasses.append("object")
                result_superclasses = ", ".join(result_superclasses)
                lines.pop(i)
                lines[i] = f"class {identifier}({result_superclasses}):"
                i += 1
            else:
                i += 1
        else:
            i += 1


def strip_superclasses(lines:list[str]):
    i = 0
    while i<len(lines)-1:
        mat1 = STRIP_SUPERCLASSES_EXCEPT.match(lines[i])
        if mat1:
            mat2 = CLASS_REGEX.match(lines[i+1])
            if mat2:
                superclasses_to_result = mat1.groups()[0].split(",")
                superclasses_to_result = set([item.strip() for item in superclasses_to_result])
                identifier, actual_superclasses = mat2.groups()
                actual_superclasses = actual_superclasses.split(",")
                actual_superclasses = set([item.strip() for item in actual_superclasses])
                result_superclasses = list(actual_superclasses.difference(superclasses_to_result))
                if not result_superclasses:
                    result_superclasses.append("object")
                result_superclasses = ", ".join(result_superclasses)
                lines.pop(i)
                lines[i] = f"class {identifier}({result_superclasses}):"
                i += 1
            else:
                i += 1
        else:
            i += 1
