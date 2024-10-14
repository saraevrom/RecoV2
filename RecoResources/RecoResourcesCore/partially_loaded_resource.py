from .resource import Resource
from typing import Optional
import warnings

class PartiallyLoadedResource(Resource):
    """
    If any resource fails to load due to missing class this resource will take their place
    """
    def __init__(self, json_data):
        self.json_data = json_data
        if "class" not in json_data.keys():
            raise ValueError("Json data of resource must contain 'class' field")
        if "data" not in json_data.keys():
            raise ValueError("Json data of resource must contain 'data' field")

    def serialize(self):
        return self.json_data

    @classmethod
    def deserialize(cls,data):
        return cls(data)

    def load_resource(self) -> Optional[Resource]:
        return Resource.unpack(self.json_data)

    def __repr__(self):
        return f"Partially loaded resource({self.json_data['class']})"
