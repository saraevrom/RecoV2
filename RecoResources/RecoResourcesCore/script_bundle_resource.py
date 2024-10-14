import inspect, os

from .resource import Resource
from typing import Optional
import warnings

from io import BytesIO
import gzip
import base64

# STRIP
from ResourcePatcher import patch_src


def compress_string(str_in):
    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(str_in.encode("utf-8"))
    return base64.b64encode(out.getvalue()).decode("utf8")


def decompress_string(b64_in):
    encoded = BytesIO(base64.b64decode(b64_in.encode("utf8")))
    with gzip.GzipFile(fileobj=encoded) as f:
        return f.read().decode("utf8")


class ScriptBundleResource(Resource):
    '''
    Makes embedding resource sources into resource storage possible
    '''
    def __init__(self, compressed_source):
        self.compressed_source = compressed_source

    # STRIP
    def strip_source(self):
        src = self.get_source()
        src = patch_src(src)
        self.compressed_source = compress_string(src)
    # END

    @classmethod
    def from_source(cls, source):
        return cls(compress_string(source))

    def get_source(self):
        return decompress_string(self.compressed_source)

    def serialize(self):
        return self.compressed_source

    @classmethod
    def deserialize(cls,data):
        return cls(data)

    def run(self, globals_=None):
        if globals_ is None:
            globals_ = {"__builtins__": __builtins__}
        src = self.get_source()
        exec (src,globals_)
        return globals_

    @classmethod
    def from_singlefile_module_name(cls, name, additional_dirs=None):
        if additional_dirs is None:
            additional_dirs = []

        src_path = None
        for add_dir in additional_dirs:
            if name+".py" in os.listdir(add_dir):
                src_path = os.path.join(add_dir,name+".py")
                break

        if src_path is None:
            mod = __import__(name, {"__builtins__": __builtins__}, dict())
            src_path = os.path.abspath(os.path.realpath(mod.__file__))

        with open(src_path,"r") as fp:
            src = fp.read()
        return cls.from_source(src)

# class IncludeResourceFile(object):
#     def __init__(self, pkg_file):
#         self.pkg_file = pkg_file
#
#     def get_file(self):
#         f = __import__(self.pkg_file,{"__builtins__": __builtins__},dict())
#         return os.path.abspath(os.path.realpath(f.__file__))
#
