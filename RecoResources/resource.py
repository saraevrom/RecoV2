import warnings
from typing import Self, Type
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout


class Resource(object):
    SUBCLASSES = None

    @classmethod
    def identifier(cls):
        return cls.__name__

    def serialize(self):
        raise NotImplementedError

    @classmethod
    def deserialize(cls,data):
        raise NotImplementedError

    def pack(self):
        return {
            "class":self.identifier(),
            "data":self.serialize()
        }

    @classmethod
    def index_subclasses(cls, force=False):
        if cls.SUBCLASSES is None or force:
            subclasses = []
            workon = [cls]
            while len(workon)>0:
                elem = workon.pop(0)
                subclasses.append(elem)
                workon.extend(elem.__subclasses__())

            cls.SUBCLASSES = subclasses

    @classmethod
    def unpack(cls, data:dict):
        Resource.index_subclasses()
        #print("CLTEST",cls.SUBCLASSES)
        for c in cls.SUBCLASSES:
            if c.identifier()==data["class"]:
                return c.deserialize(data["data"])
        print("Available subclasses:",[i.__name__ for i in cls.SUBCLASSES])
        raise ValueError(f"Unknown resource of type {data['class']}")

    @classmethod
    def try_transform(cls, data):
        Resource.index_subclasses()
        # print("CLTEST",cls.SUBCLASSES)
        for c in cls.SUBCLASSES:
            test = c.try_from(data)
            if test is not None:
                return test
        return None

    def unwrap(self):
        return self

    @classmethod
    def try_from(cls,x):
        return None


class ResourceStorage(object):
    def __init__(self):
        self.resources = dict()

    def update_with(self, other:Self):
        self.resources.update(other.resources)

    def clear(self):
        self.resources.clear()

    def serialize(self):
        print(self.resources)
        return {k:self.resources[k].pack() for k in self.resources.keys()}

    def set_resource(self,key,resource:Resource):
        self.resources[key] = resource

    def has_resource(self,key):
        return key in self.resources.keys()

    def try_get(self,key):
        if self.has_resource(key):
            return self.get(key)
        return None

    def set(self,key,value):
        if isinstance(value,Resource):
            resource = value
        else:
            resource = Resource.try_transform(value)
        if resource is None:
            warnings.warn(f"WARNING: Resource {type(value)} is not transformable")
            return
        self.resources[key] = resource

    def get_resource(self,key):
        return self.resources[key]

    def get(self,key):
        return self.get_resource(key).unwrap()

    def delete_resource(self,key):
        if key in self.resources.keys():
            del self.resources[key]

    @classmethod
    def deserialize(cls,data:dict)->Self:
        workon = ResourceStorage()
        resources = {k:Resource.unpack(data[k]) for k in data.keys()}
        workon.resources = resources
        return workon

