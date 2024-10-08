from .resource import Resource
from typing import Optional
import warnings

from io import BytesIO
import gzip
import base64


def compress_string(str_in):
    out = BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(str_in.encode("utf-8"))
    return base64.b64encode(out.getvalue())


def decompress_string(b64_in):
    encoded = BytesIO(base64.b64decode(b64_in))
    with gzip.GzipFile(fileobj=encoded) as f:
        return f.read().decode("utf8")


class ScriptBundleResource(Resource):
    '''
    Makes embedding resource sources into resource storage possible
    '''
    def __init__(self, compressed_source):
        self.compressed_source = compressed_source

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
            globals_ = dict()
        src = self.get_source()
        exec (src,globals_)
        return globals_