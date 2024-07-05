import re
import sqlite3
from typing import Type
from .star import Star, StarList

BAYER_LIST = "Alp Bet Gam Del Eps Zet Eta The Iot Kap Lam Mu Nu Xi Omi Pi Rho Sig Tau Ups Phi Chi Psi Ome".split(" ")
BAYER_LETTER_PART = "(?:"+"|".join(BAYER_LIST)+")"
BAYER_REGEX = rf"{BAYER_LETTER_PART}(?:-?\d)?"


def wrap_star(star):
    if star is None:
        return None
    return [star]

def match_by_group(match, field):
    group = match.group()
    star = Star.fetch_sql(f"SELECT * FROM stars WHERE {field}=?", [group])
    return wrap_star(star)
    #return database[database[field] == match.group()]


def match_by_first_group(match, field, cast_type: Type = int):
    target = cast_type(match.groups()[0])
    #print("MATCH", field, target)
    star = Star.fetch_sql(f"SELECT * FROM stars WHERE {field}==?",[target])
    return wrap_star(star)
    #res = database[database[field] == target]
    #print(res)
    #return res


def match_by_dual(match, field1, field2, cast1: Type = str, cast2: Type = str, grp1=0, grp2=1):
    #print(match.groups())
    #print(f"{field1}-{field2} match")
    grps = match.groups()
    target1 = cast1(grps[grp1])
    target2 = cast2(grps[grp2])
    star = Star.fetch_sql(f"SELECT * FROM stars WHERE {field1}=? AND {field2}=?", [target1,target2])
    return wrap_star(star)
    #print(f"targets {target1}; {target2}")
    # m1 = database[field1] == target1
    # m2 = database[field2] == target2
    # res = database[m1 & m2]
    # return res


def match_sql_where(match):
    grp = match.groups()[0]
    print("SQL GRP",grp)
    if grp:
        try:
            stars = StarList.fetch_sql("SELECT * FROM stars WHERE "+grp,[]).stars
            if stars:
                return stars
            return None
        except sqlite3.OperationalError:
            return None
    else:
        return None

filters = [
    [r"\s+", None],
    [r"WHERE\s*\(([^)]*)\)",match_sql_where],
    #[r"Gliese\s*(\d+)", lambda x: match_by_first_group(x, "gl")],
    #[r"HIP\s*(\d+)", lambda x: match_by_first_group(x, "hip")],
    [r"HR\s*(\d+)", lambda x: match_by_first_group(x, "hr")],
    [r"HD\s*(\d+)", lambda x: match_by_first_group(x, "hd")],
    #[r"Gl\s*(\d+)", lambda x: match_by_first_group(x, "gl")],
    [rf'({BAYER_REGEX})\s+(\w+)', lambda x: match_by_dual(x,"bayer","constellation")], # Bayer match
    [r'(\d+)\s+(\w+)', lambda x: match_by_dual(x,"flamsteed","constellation", cast1=int)], # Flamsteed match
    [r"\w+", lambda x: match_by_group(x, "proper")],
]

for i in range(len(filters)):
    filters[i][0] = re.compile(filters[i][0])


def get_ids(entries):
    return [item["id"] for item in entries]


def parse_stars(asked_string):
    ptr = 0
    stars = StarList.new_empty()
    #database = get_database()
    while ptr < len(asked_string):
        mat_pair = None
        for filt in filters:
            regex: re.Pattern
            regex, processor = filt
            mat = regex.match(asked_string[ptr:])
            if mat:
                mat_pair = mat, processor
                break
        if mat_pair is None:
            #print("Unknown pattern on", ptr)
            return None
        else:
            mat, proc = mat_pair
            ptr += mat.end()
            if proc is not None:
                add_stars = proc(mat)
                if add_stars is not None:
                    for star in add_stars:
                        stars.append(star)
                    #print("Found", star)
                else:
                    #print("No star")
                    return None
    #print("PARSE COMPLETED")
    return stars
