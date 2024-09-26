from typing import List, Optional, Type, Union

import matplotlib.pyplot as plt

from RecoResources import ResourceRequest, ResourceStorage, ResourceDisplay, DisplayList


class ExposedClassMethod(object):
    def __init__(self,cls,method):
        self.cls = cls
        self.method = method

    def __call__(self,*args,**kwargs):
        self.method.__func__(self.cls,*args,**kwargs)

class LabelledCallable(object):
    def __init__(self,func, label):
        self.func = func
        self.label = label

    def __repr__(self):
        return f"<Function ({self.func}) with name {self.label}>"

    def __call__(self,*args,**kwargs):
        self.func(*args,**kwargs)


class LabelledAction(object):
    def __init__(self,label):
        self.label = label

    def __call__(self,func):
        if not isinstance(func,staticmethod):
            print("Action is not static method. Applying decorator @staticmethod...")
            func = staticmethod(func)
        return LabelledCallable(func, self.label)

class SceneEventResult(object):
    def __init__(self,redraw:bool,update_resources:bool):
        self.redraw = redraw
        self.update_resources = update_resources

    @classmethod
    def noop(cls):
        pass

class Scene(object):
    SceneName = "Scene"

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        pass

    @classmethod
    def on_scene_mouse_event(cls, resources: ResourceStorage, event):
        return True


class ReconstructionModel(object):
    RequestedResources = ResourceRequest()
    AdditionalLabels = dict()
    Scenes: List[Type[Union[Scene, str]]] = []
    DisplayList:Optional[DisplayList] = None

    # def __init__(self):
    #     self.resource_storage = ResourceStorage()
    #     self._request = self

    @classmethod
    def calculate(cls, resources:ResourceStorage):
        raise NotImplementedError

    @classmethod
    def draw_scene(cls, resources:ResourceStorage, fig:plt.Figure,axes:plt.Axes, scene):
        for s in cls.Scenes:
            if s.SceneName == scene:
                return s.draw_scene(resources, fig,axes)

    @classmethod
    def on_scene_mouse_event(cls, resources:ResourceStorage,event, scene):
        for s in cls.Scenes:
            if s.SceneName == scene:
                return s.on_scene_mouse_event(resources,event)

    @classmethod
    def get_scene_names(cls):
        if not cls.Scenes:
            return []
        if isinstance(cls.Scenes[0],str):
            return cls.Scenes
        else:
            return [scene.SceneName for scene in cls.Scenes]

    # def output(self,data_display:ResourceDisplay):
    #     labels = self.RequestedResources.labels()
    #     labels.update(self.AdditionalLabels)
    #     data_display.show_resources(self.resource_storage, labels)

    @classmethod
    def get_actions(cls):
        res = dict()
        for key in cls.__dict__.keys():
            class_field = getattr(cls,key)
            if isinstance(class_field,LabelledCallable):
                res[key] = (class_field.label, class_field)
        return res


# To make old models work. Oops
ReconsructionModel = ReconstructionModel