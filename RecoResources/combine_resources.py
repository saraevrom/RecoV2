from typing import Dict
from PyQt6.QtWidgets import QFrame, QWidget, QVBoxLayout, QLabel

from RecoResources import Resource, ResourceInput, ResourceForm, ResourceOutput, ResourceRequest, ResourceInputWidget, \
    ResourceStorage

from RecoResources import ResourceDisplay
from RecoResources.strict_functions import Default


class CombineResourceInput(ResourceInputWidget):
    def __init__(self, request, bound_resource_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bound_resource_class = bound_resource_class
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.label = QLabel("")
        self.label.setVisible(False)
        layout.addWidget(self.label)
        frame = QFrame()
        layout.addWidget(frame)
        frame_layout = QVBoxLayout()
        frame_layout.setContentsMargins(0,0,0,0)
        frame.setLayout(frame_layout)
        self.input = ResourceForm(request)
        frame_layout.addWidget(self.input)
        self.input.changed_callback = self.trigger_callback

    def set_title(self,title):
        self.label.setVisible(True)
        self.label.setText(title)

    def get_resource(self):
        stor = self.input.get_resources()
        return self.bound_resource_class(stor)

    def set_resource(self,resource):
        self.input.set_resources(resource.data)


class CombineResource(Resource,ResourceInput,ResourceOutput,Default):
    Fields: ResourceRequest
    InputWidget = CombineResourceInput

    def __init__(self, data: ResourceStorage):
        self.data = data

    def __repr__(self):
        data = [f'"{k}": {self.data.resources[k]}' for k in self.data.resources.keys()]
        data = ", ".join(data)
        return f"{type(self).__name__}{{{data}}}"

    def serialize(self):
        # print("Combined",type(self))
        # print("Combined",self.data)
        return self.data.serialize()

    @classmethod
    def deserialize(cls,data):
        return cls(ResourceStorage.deserialize(data))

    @classmethod
    def create_widget(cls, *args, **kwargs):
        return cls.InputWidget(cls.Fields,cls,*args,**kwargs)

    def show_data(self, label:str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        layout.addWidget(QLabel(label))

        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        flayout = QVBoxLayout()
        frame.setLayout(flayout)
        layout.addWidget(frame)

        #flayout.addWidget(self.value.show_data("Chosen variant"))
        display = ResourceDisplay()
        display.show_resources(self.data, self.Fields.labels())
        flayout.addWidget(display)

        return widget

    def unwrap(self):
        return self.data

    @classmethod
    def default(cls):
        return cls(None)
