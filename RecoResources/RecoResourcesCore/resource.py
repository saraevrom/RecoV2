import gc
import traceback
import warnings
from typing import Type, Self
from datetime import datetime

#Stripping data for short resource declaration
STRIP_ATTRIBUTES = [
    "InputWidget", "create_widget", "input_is_available",
    "show_data", "output_is_available", "pack_source" "source_dependencies"
]
STRIP_SUPERCLASSES = ["ResourceInput", "ResourceOutput", "Default"]


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

    @classmethod
    def creation_time(cls):
        if not hasattr(cls, "__creation_time"):
            setattr(cls,"__creation_time",datetime.now())
        return getattr(cls, "__creation_time")

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
        if force:
            cls.SUBCLASSES = None # Remove old resources to make them targets for GC
        gc.collect()
        if cls.SUBCLASSES is None:
            subclasses = dict()
            # res = []
            workon = [cls]
            while len(workon)>0:
                elem = workon.pop(0)
                key = elem.identifier()
                if key in subclasses:
                    if elem.creation_time()>subclasses[key].creation_time():
                        subclasses[key] = elem
                else:
                    subclasses[key] = elem
                # res.append(elem)
                workon.extend(elem.__subclasses__())

            # print("INDEXED", res)
            cls.SUBCLASSES = list(subclasses.values())

    @classmethod
    def unpack(cls, data:dict):
        """
        Recover resource made with pack() function. Will guess its type.
        """
        Resource.index_subclasses()
        #print("CLTEST",cls.SUBCLASSES)
        # for c in cls.SUBCLASSES:
        #     if c.identifier()==data["class"]:
        #         return c.deserialize(data["data"])
        c = cls.lookup_resource(data["class"])
        return c.deserialize(data["data"])

    @classmethod
    def lookup_resource(cls, identifier) -> Self:
        Resource.index_subclasses()
        for c in cls.SUBCLASSES:
            if c.identifier() == identifier:
                return c
        raise ValueError(f"Unknown resource of type {identifier}")

    @classmethod
    def unpack_safe(cls, data:dict):
        """
        Recover resource made with pack() function. Will guess its type.
        If resource fails to load it will be returned as PartiallyLoadedResource
        """
        from .partially_loaded_resource import PartiallyLoadedResource
        try:
            res = cls.unpack(data)
            return res
        except ValueError:
            return PartiallyLoadedResource(data)

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

    def __eq__(self, other):
        return self.identifier()==other.identifier()

    # STRIP
    def resetable(self):
        return False

    def reset(self):
        raise NotImplementedError

    # END

class ResourceStorage(object):
    """
    Container class for resources
    """
    def __init__(self):
        self.resources = dict()
        self.loaded_resources_bundles_track = dict()

    def update_with(self, other, except_data=None):
        if except_data is None:
            except_data = []
        for key in other.resources.keys():
            if key not in except_data:
                self.resources[key] = other.resources[key]
        self.loaded_resources_bundles_track.update(other.loaded_resources_bundles_track)


    def clear(self):
        """
        Remove all resources
        """
        self.resources.clear()
        self.loaded_resources_bundles_track.clear()

    def serialize(self):
        """
        Turn resources into JSON serializable object
        """
        #print(self.resources)
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

    def has_resources(self,*keys):
        own_keys = set(list(self.resources.keys()))
        keys1 = set(keys)
        return keys1.issubset(own_keys)

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
        resources = {k:Resource.unpack_safe(data[k]) for k in data.keys()}
        workon.resources = resources
        return workon

    def try_load_partial_resources(self):
        from .partially_loaded_resource import PartiallyLoadedResource
        for key in self.resources.keys():
            src = self.resources[key]
            if isinstance(src, PartiallyLoadedResource):
                try:
                    res = src.load_resource()
                    self.resources[key] = res
                except ValueError:
                    warnings.warn(f"Failed to load resource {src.json_data['class']}")

    def load_bundles(self):
        from .script_bundle_resource import ScriptBundleResource
        for key in self.resources.keys():
            src = self.resources[key]
            if isinstance(src, ScriptBundleResource):
                globs = {"__builtins__": __builtins__}
                try:
                    globs = src.run(globs)
                    success = True
                except Exception: # Will print traceback. No silencing
                    print("Loading bundle error")
                    print(traceback.format_exc())
                    success = False
                if success:
                    self.loaded_resources_bundles_track[key] = globs
                    Resource.index_subclasses(True)
                # Why not outside the loop?
                # To make resource instantly available for next ones.
        gc.collect()

    # STRIP
    def get_resetables(self):
        return [k for k in self.resources.keys() if self.resources[k].resetable()]
    # END