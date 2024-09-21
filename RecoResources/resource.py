import warnings
from typing import Type
from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout


class Resource(object):
    """
    Base resource class
    """
    SUBCLASSES = None

    @classmethod
    def identifier(cls):
        """
        Identifier of class for pack/unpack
        """
        return cls.__name__

    def serialize(self):
        """
        Save data to a json serializable data
        """
        raise NotImplementedError

    @classmethod
    def deserialize(cls,data):
        """
        Load resource from given data
        """
        raise NotImplementedError

    def pack(self):
        """
        Serialize data and add class identifier to make resource fully recoverable
        """
        return {
            "class":self.identifier(),
            "data":self.serialize()
        }

    @classmethod
    def index_subclasses(cls, force=False):
        """
        See what resources types do we have
        """
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
        """
        Recover resource made with pack() function. Will guess its type.
        """
        Resource.index_subclasses()
        #print("CLTEST",cls.SUBCLASSES)
        for c in cls.SUBCLASSES:
            if c.identifier()==data["class"]:
                return c.deserialize(data["data"])
        print("Available subclasses:",[i.__name__ for i in cls.SUBCLASSES])
        raise ValueError(f"Unknown resource of type {data['class']}")

    @classmethod
    def try_transform(cls, data):
        """
        Attempts to create resource from other type by picking suiting resource
        """
        Resource.index_subclasses()
        # print("CLTEST",cls.SUBCLASSES)
        for c in cls.SUBCLASSES:
            test = c.try_from(data)
            if test is not None:
                return test
        return None

    def unwrap(self):
        '''
        Extract stored data from resource
        '''
        return self

    @classmethod
    def try_from(cls,x):
        """
        Tries to make this resource from other type. Returns None if fails
        """
        return None


class ResourceStorage(object):
    """
    Container class for resources
    """
    def __init__(self):
        self.resources = dict()

    def update_with(self, other):
        self.resources.update(other.resources)

    def clear(self):
        """
        Remove all resources
        """
        self.resources.clear()

    def serialize(self):
        """
        Turn resources into JSON serializable object
        """
        print(self.resources)
        return {k:self.resources[k].pack() for k in self.resources.keys()}

    def set_resource(self,key,resource:Resource):
        """
        Sets the resource to assigned key
        """
        self.resources[key] = resource

    def has_resource(self,key):
        """
        Checks if resource with given key exists
        """
        return key in self.resources.keys()

    def try_get(self,key):
        """
        Works like get(key) but if resource does not exist returns None
        """
        if self.has_resource(key):
            return self.get(key)
        return None

    def set(self,key,value):
        """
        Sets the resource to assigned key. Tries to infer resource type from other types
        """
        if isinstance(value,Resource):
            resource = value
        else:
            resource = Resource.try_transform(value)
        if resource is None:
            warnings.warn(f"WARNING: Resource {type(value)} is not transformable")
            return
        self.resources[key] = resource

    def get_resource(self,key):
        """
        Gets the resource from assigned key.
        """
        return self.resources[key]

    def get(self,key):
        """
        Gets the resource from assigned key. Tries to unwrap stored value
        """
        return self.get_resource(key).unwrap()

    def delete_resource(self,key):
        """
        Deletes resource with given key
        """
        if key in self.resources.keys():
            del self.resources[key]

    @classmethod
    def deserialize(cls,data:dict):
        """
        Restore resource storage from JSON serializable data.
        """
        workon = ResourceStorage()
        resources = {k:Resource.unpack(data[k]) for k in data.keys()}
        workon.resources = resources
        return workon

