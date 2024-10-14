import os
from pathlib import Path
from .copy_paste import copy_file_stripping

def copy_obj(src_path, dst_path, total_exceptions=None):
    if total_exceptions is None:
        total_exceptions = []
    #print(f"{src_path} -> {dst_path}")
    src = Path(src_path)
    dst = Path(dst_path)
    if src.is_dir():
        dst.mkdir(exist_ok=True,parents=True)
        nocopy = src.joinpath("nocopy.txt")
        if nocopy.is_file():
            with nocopy.open("r") as fp:
                exclude_files = fp.read().split("\n")
                exclude_files = [item.strip() for item in exclude_files]
                exclude_files = [item for item in exclude_files if item]
        else:
            exclude_files = []
        exclude_files += total_exceptions
        exclude_files.append("nocopy.txt")
        for item in src.iterdir():
            if item.name not in exclude_files:
                tgt = dst.joinpath(item.relative_to(src))
                copy_obj(item,tgt,total_exceptions)
    else:
        copy_file_stripping(src, dst)