import inspect

from typing import Optional, Dict, List, Union, Type

from PyQt6.QtWidgets import QVBoxLayout, QLabel, QFrame, QComboBox, QWidget

from RecoResources import Resource, ResourceInput, ResourceInputWidget, ResourceOutput
from RecoResources.strict_functions import StrictReturnFunction, Default

from collections import OrderedDict


class ResourceVariant(object):
    def __init__(self, default_value_creator:Union[StrictReturnFunction,Type[Default]], display_name:Optional[str]=None):
        if inspect.isclass(default_value_creator) and issubclass(default_value_creator,Default):
            default_value_creator = default_value_creator.to_strict_function()
        self.default_value_creator = default_value_creator
        self.display_name = display_name

    def get_default_value_type(self):
        from RecoResources.basic_resources import remap_basic_types
        return remap_basic_types(self.default_value_creator.return_type)

    def create_default(self):
        from RecoResources.basic_resources import remap_basic_values
        return remap_basic_values(self.default_value_creator())

    def create_widget(self,*args,**kwargs):
        from RecoResources.basic_resources import remap_basic_values
        return remap_basic_values(self.default_value_creator()).create_widget(*args,**kwargs)

    def get_displayname(self,key):
        if self.display_name is None:
            return f"Variant: {key}"
        else:
            return self.display_name


class AlternativeResourceInput(ResourceInputWidget):
    def __init__(self,variants:List[ResourceVariant],reference_alter,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.reference_alter = reference_alter
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self._label = QLabel("")
        self._label.setVisible(False)
        main_layout.addWidget(self._label)
        self.subfields = [None]*len(variants)
        self.variants = variants
        self.variant_types = [v.get_default_value_type() for v in variants]

        self._selector = QComboBox()
        main_layout.addWidget(self._selector)
        for i,x in enumerate(self.variants):
            self._selector.addItem(x.get_displayname(i))
        self._selector.currentIndexChanged.connect(self._on_selector_update)

        self._layout = QVBoxLayout()
        self.frame = QFrame()
        self.frame.setLayout(self._layout)
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._layout.setContentsMargins(0,0,0,0)

        main_layout.addWidget(self.frame)
        self.select_variant(0)



    def _on_selector_update(self):
        i = self._selector.currentIndex()
        self.select_variant(i)

    def ensure_variant(self,index:int):
        if self.subfields[index] is None:
            self.subfields[index] = self.variants[index].create_widget()
            self._layout.addWidget(self.subfields[index])
            #self.subfields[index].setMinimumWidth(300)

    def select_variant(self,index:int):
        self.ensure_variant(index)
        for i,x in enumerate(self.subfields):
            if x is not None:
                x.setVisible(i == index)
        self._selector.setCurrentIndex(index)
        #self.recalculate_height()
        # if self.controller is not None:
        #     self.controller.recalculate_height()

    def get_resource(self):
        index = self._selector.currentIndex()
        return self.reference_alter(self.subfields[index].get_resource())

    def set_resource(self,resource):
        print("ALTER SET", resource)
        index = self.variant_types.index(type(resource.value))
        self.select_variant(index)
        self.subfields[index].set_resource(resource.value)

    def set_title(self,title):
        self._label.setVisible(True)
        self._label.setText(title)


def validate_variants(variants:List[ResourceVariant]):
    typeset = set()
    for variant in variants:
        if variant.default_value_creator.return_type in typeset:
            raise TypeError("variant types must be unique")
        typeset.add(variant.default_value_creator.return_type)


class AlternatingResource(Resource,ResourceInput, ResourceOutput, Default):
    Variants: List[ResourceVariant]
    InputWidget = AlternativeResourceInput

    def __init__(self,value:Optional[Resource]=None):
        validate_variants(self.Variants)
        if value is None:
            value = self.Variants[0].create_default()

        variant_missing = True
        for var in self.Variants:
            if var.get_default_value_type() == type(value):
                variant_missing = False
                break
        if variant_missing:
            raise ValueError(f"Choice variant type is invalid for variant set")

        self.value = value

    @classmethod
    def default(cls):
        return cls()

    def __repr__(self):
        return f"{type(self).__name__}({self.value})"

    def serialize(self):
        return self.value.pack()

    @classmethod
    def deserialize(cls,data):
        unpacked = Resource.unpack(data)
        #print("ALT deser", data, unpacked)
        return cls(unpacked)

    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(cls.Variants,cls,*args,**kwargs)

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

        display = ""
        for var in self.Variants:
            if var.get_default_value_type() == type(self.value):
                display = var.display_name
                break
        type(self.value)
        flayout.addWidget(self.value.show_data(f"Chosen variant: {display}"))
        return widget

    def unwrap(self):
        return self.value.unwrap()
