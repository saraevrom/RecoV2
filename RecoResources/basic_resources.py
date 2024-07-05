from typing import Dict, Type

from PyQt6.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QCheckBox, QWidget, QComboBox
from RecoResources import ResourceInput, Resource, ResourceInputWidget, ResourceOutput
from RecoResources.strict_functions import Default


class ValuedResourceInput(ResourceInputWidget):
    BaseType = None
    DefaultValue = None
    ConnectedResource = None

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)

        self._label = QLabel("")
        self._layout.addWidget(self._label,0)
        self._entry =  QLineEdit(str(self.DefaultValue))
        self._last_data = self.DefaultValue
        self._layout.addWidget(self._entry,1)

        self._default_stylesheet = self._entry.styleSheet()
        #self.setFixedHeight(40)

        #policy = QSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
        #self.setSizePolicy(policy)
        #self._entry.setSizePolicy(policy)
        self._entry.textChanged.connect(self.on_changed)
        self.on_changed()


    def on_changed(self):
        try:
            self._last_data = self.BaseType(self._entry.text())
            self._entry.setStyleSheet(self._default_stylesheet)
        except ValueError:
            #print("ParseFail")
            self._entry.setStyleSheet("color: red;")

    def get_resource(self):
        #print(self._last_data)
        return self.ConnectedResource(self._last_data)

    def set_resource(self,resource):
        self._entry.setText(str(resource.value))
        self._last_data = resource.value

    def set_title(self,title):
        self._label.setText(title)


class ValuedResource(Resource,ResourceInput, ResourceOutput):
    BaseType = None
    def __init__(self,value):
        self.value = value

    def __repr__(self):
        return f"{type(self).__name__}=({self.value})"

    def serialize(self):
        return self.value

    @classmethod
    def deserialize(cls,data):
        return cls(data)

    def show_data(self, label:str) ->QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        widget.setLayout(layout)
        layout.addWidget(QLabel(label))

        non_editable_line_edit = QLineEdit(str(self.value))
        non_editable_line_edit.setReadOnly(True)

        layout.addWidget(non_editable_line_edit)
        return widget

    def unwrap(self):
        return self.value

    @classmethod
    def try_from(cls,x):
        if cls.BaseType is None:
            return None
        if isinstance(x,cls.BaseType):
            return cls(x)
        return None


class IntegerResourceInput(ValuedResourceInput):
    BaseType = int
    DefaultValue = 0
    ConnectedResource = 0


class IntegerResource(ValuedResource):
    InputWidget = IntegerResourceInput
    BaseType = int


IntegerResourceInput.ConnectedResource = IntegerResource


class FloatResourceInput(ValuedResourceInput):
    BaseType = float
    DefaultValue = 0.0
    ConnectedResource = 0


class FloatResource(ValuedResource):
    InputWidget = FloatResourceInput
    BaseType = float


FloatResourceInput.ConnectedResource = FloatResource


class StringResourceInput(ValuedResourceInput):
    BaseType = str
    DefaultValue = ""
    ConnectedResource = 0


class StringResource(ValuedResource):
    BaseType = str
    InputWidget = StringResourceInput


StringResourceInput.ConnectedResource = StringResource



class BooleanResourceInput(ResourceInputWidget):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)

        self._check = QCheckBox("")
        self._layout.addWidget(self._check)


    def get_resource(self):
        return BooleanResource(self._check.isChecked())

    def set_resource(self,resource):
        self._check.setChecked(resource.value)

    def set_title(self,title):
        self._check.setText(title)


class BooleanResource(ValuedResource):
    InputWidget = BooleanResourceInput
    BaseType = bool


BASE_MAPPING = {
        int:IntegerResource,
        float:FloatResource,
        str:StringResource,
        bool:BooleanResource
    }


def remap_basic_values(t):
    if type(t) in BASE_MAPPING.keys():
        return BASE_MAPPING[type(t)](t)
    return t


def remap_basic_types(t):
    if t in BASE_MAPPING.keys():
        return BASE_MAPPING[t]
    return t


class BlankResourceInput(ResourceInputWidget):

    def __init__(self,bound_type,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.bound_type = bound_type
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)

        self._title = QLabel("")
        self._layout.addWidget(self._title)
        self._layout.addWidget(QLabel(self.bound_type.Label))

    def set_title(self,title):
        self._title.setText(title)

    def set_resource(self,resource):
        pass

    def get_resource(self):
        print(self.bound_type)
        return self.bound_type()


class BlankResource(Resource, ResourceInput, ResourceOutput, Default):
    Label: str = "FIXME"
    InputWidget = BlankResourceInput

    def __init__(self):
        pass

    def serialize(self):
        return None

    @classmethod
    def deserialize(cls,data):
        print("Deserialize called")
        return cls()

    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(cls,*args,**kwargs)

    def show_data(self, label:str) -> QWidget:
        res = QWidget()
        layout = QHBoxLayout()
        res.setLayout(layout)
        layout.addWidget(QLabel(label))
        layout.addWidget(QLabel(self.Label))
        return res

    def __repr__(self):
        return f"{type(self).__name__}=({self.Label})"

    def unwrap(self):
        return None

    @classmethod
    def default(cls):
        return cls()

    @classmethod
    def try_from(cls,x):
        if x is None:
            return cls()
        return None



class ChoiceInput(ResourceInputWidget):
    def __init__(self,ref,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.ref = ref
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)
        self._label = QLabel("")
        self._combo = QComboBox()
        for key in ref.Choices.keys():
            v = ref.Choices[key]
            self._combo.addItem(v,key)
        self.keys = list(ref.Choices.keys())
        self._layout.addWidget(self._label)
        self._layout.addWidget(self._combo)

    def set_title(self,title):
        self._label.setText(title)

    def set_resource(self,resource):
        key = resource.value
        index = self.keys.index(key)
        self._combo.setCurrentIndex(index)

    def get_resource(self):
        return self.ref(self.keys[self._combo.currentIndex()])


class ChoiceResource(Resource, Default, ResourceInput, ResourceOutput):
    Choices:Dict[str,str]
    InputWidget = ChoiceInput

    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(cls)

    def __init__(self,value):
        if len(self.Choices.keys()) == 0:
            raise TypeError(f"Class {type(self)} has no choices")
        if value not in self.Choices.keys():
            raise ValueError(f"Value {value} is not a valid choice")
        self.value = value

    @classmethod
    def default(cls):
        if len(cls.Choices.keys()) == 0:
            raise TypeError(f"Class {cls} has no choices")
        return cls(list(cls.Choices.keys())[0])

    def serialize(self):
        return self.value

    @classmethod
    def deserialize(cls,data):
        return cls(data)

    def unwrap(self):
        return self.value

    def show_data(self, label:str) ->QWidget:
        res = QWidget()
        layout = QHBoxLayout()
        res.setLayout(layout)
        layout.addWidget(QLabel(label))
        layout.addWidget(QLabel(self.Choices[self.value]))
        return res
