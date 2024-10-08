from typing import Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QLabel
from RecoResources.core.resource import ResourceStorage


class DisplayList(object):
    def __init__(self,is_white:bool,display_list:list):
        self.is_white = is_white
        self.display_list = display_list

    def is_allowed(self,item):
        return (item in self.display_list) == self.is_white

    @staticmethod
    def whitelist(display_list):
        return DisplayList(True,display_list)

    @staticmethod
    def blacklist(display_list):
        return DisplayList(False,display_list)

    @staticmethod
    def default():
        return DisplayList.blacklist([])


class ResourceOutput(object):
    def show_data(self, label:str)->QWidget:
        raise NotImplementedError

    @classmethod
    def output_is_available(cls):
        return True


class ResourceDisplay(QWidget):
    def __init__(self,placeholder="Outputs",*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.addWidget(QLabel(placeholder))
        self._placeholder = placeholder

    def show_resources(self,resource_storage:ResourceStorage, labels:dict, allow_list:Optional[DisplayList]=None):
        if allow_list is None:
            allow_list = DisplayList.default()

        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().setParent(None)

        if not resource_storage.resources:
            self._layout.addWidget(QLabel(self._placeholder))

        for resource_key in resource_storage.resources.keys():
            resource = resource_storage.resources[resource_key]
            if (isinstance(resource,ResourceOutput) and resource.output_is_available()
                    and allow_list.is_allowed(resource_key)):
                frame = QFrame()
                frame_layout = QVBoxLayout()
                frame.setLayout(frame_layout)
                frame_layout.setContentsMargins(0,0,0,0)
                frame.setFrameShape(QFrame.Shape.StyledPanel)
                if resource_key in labels.keys():
                    label = labels[resource_key]
                else:
                    label = f"Resource: {resource_key}"
                output_widget = resource.show_data(label)
                frame_layout.addWidget(output_widget)
                self._layout.addWidget(frame)
