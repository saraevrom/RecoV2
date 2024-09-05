from typing import Optional, Dict, List, Any

from PyQt6.QtWidgets import QVBoxLayout, QLabel, QFrame, QCheckBox, QWidget

from RecoResources import Resource, ResourceInput, ResourceInputWidget, ResourceOutput
from RecoResources.strict_functions import StrictReturnFunction


class OptionResourceInput(ResourceInputWidget):
    def __init__(self,reftype,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.reftype = reftype

        main_layout = QVBoxLayout()
        #main_layout.setContentsMargins(0,0,0,0)
        self.setLayout(main_layout)
        #self._label = QLabel("")
        #main_layout.addWidget(self._label)
        self.subfield = None

        self._selector = QCheckBox("")
        main_layout.addWidget(self._selector)

        self._layout = QVBoxLayout()
        self.frame = QFrame()
        self.frame.setLayout(self._layout)
        self._layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(self.frame)
        self._selector.checkStateChanged.connect(self.on_toggle)

    def on_toggle(self):
        if self._selector.isChecked():
            self.ensure_subfield()
            self.subfield.setVisible(True)
        else:
            if self.subfield is not None:
                self.subfield.setVisible(False)
        self.trigger_callback()

    def ensure_subfield(self):
        if self.subfield is None:
            self.subfield = self.reftype.OptionType.create_widget()
            print(self.subfield)
            self._layout.addWidget(self.subfield)

    def set_title(self,title):
        self._selector.setText(title)

    def get_resource(self):
        if self._selector.isChecked():
            return self.reftype(self.subfield.get_resource())
        else:
            return self.reftype(None)

    def set_resource(self,resource):
        if resource.is_some():
            self._selector.setChecked(True)
            self.subfield.set_resource(resource.value)
        else:
            self._selector.setChecked(False)
        self.on_toggle()

class OptionResource(Resource,ResourceInput, ResourceOutput):
    OptionType:Resource
    InputWidget = OptionResourceInput

    def __init__(self, value:Optional[Any]):
        if self.OptionType is None:
            raise TypeError("Option type is not set")
        if value is not None and type(value) is not self.OptionType:
            raise ValueError(f"Value type {type(value)} does not match option type {self.OptionType}")
        self.value = value

    def __repr__(self):
        if self.value is None:
            postfix = "None"
        else:
            postfix = f"Some({self.value})"
        return f"{type(self).__name__}.{postfix}"

    def serialize(self):
        if self.value is None:
            return None
        else:
            return self.value.pack()

    @classmethod
    def deserialize(cls,data):
        if data is None:
            return cls(None)
        else:
            unpacked = Resource.unpack(data)
            print("Opt DESER",data)
            print("Opt DESER RES",unpacked)
            return cls(unpacked)

    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(cls,*args,**kwargs)

    def is_some(self):
        return self.value is not None

    def show_data(self, label:str) ->QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        layout.addWidget(QLabel(label))

        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        flayout = QVBoxLayout()
        frame.setLayout(flayout)
        layout.addWidget(frame)

        if self.value is not None:
            flayout.addWidget(self.value.show_data("Value"))
        else:
            flayout.addWidget(QLabel("None"))
        return widget

    def unwrap(self):
        if self.value is None:
            return None
        else:
            return self.value.unwrap()