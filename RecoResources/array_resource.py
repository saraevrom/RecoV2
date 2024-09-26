from typing import Dict

from PyQt6.QtGui import QDrag
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtWidgets import QFrame, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QFrame

from RecoResources import Resource, ResourceInput, ResourceForm, ResourceOutput, ResourceRequest, ResourceInputWidget, \
    ResourceStorage, BlankResource

from RecoResources import ResourceDisplay
from RecoResources.strict_functions import Default


class ArrayItemDragger(QLabel):
    def __init__(self, upper_container, parent=None):
        super().__init__(parent=parent, text="Drag me")
        self.upper_container = upper_container
        self.setFrameShape(QFrame.Shape.StyledPanel)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.start_drag()

    def start_drag(self):
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(f"{self.upper_container.get_identifier()} {self.upper_container.get_index()}")
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)


class ArrayItemWidget(QFrame):
    def __init__(self, refclass: type[ResourceInput], container, parent=None):
        super().__init__(parent=parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.refclass = refclass
        self.contaner = container

        self._toppanel = QFrame()
        #self._toppanel.setFrameShape(QFrame.Shape.StyledPanel)
        toppanel_layout = QHBoxLayout()
        self._toppanel.setLayout(toppanel_layout)

        self._dragger = ArrayItemDragger(self)
        toppanel_layout.addWidget(self._dragger)

        self._delete_btn = QPushButton()
        self._delete_btn.setText("Delete")
        self._delete_btn.clicked.connect(self.on_delete)
        toppanel_layout.addWidget(self._delete_btn)

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self._layout.addWidget(self._toppanel)

        self._main_widget = refclass.create_widget()
        self._layout.addWidget(self._main_widget)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, a0):
        if a0.mimeData().hasText():
            splitted = a0.mimeData().text().split(" ")
            if len(splitted) == 2 and splitted[0] and splitted[1].isnumeric():
                # print("SOURCE", splitted)
                # print("TARGET", self.get_identifier())
                if splitted[0] == self.get_identifier():
                    a0.acceptProposedAction()

    def dropEvent(self, a0):
        #self.setText()
        swap_index = int(a0.mimeData().text().split(" ")[1])
        my_index = self.get_index()
        self.contaner.swap_items(my_index, swap_index)
        a0.acceptProposedAction()

    def get_identifier(self):
        c = self.contaner.bound_resource_class.identifier()
        num = self.contaner.widget_identifier
        return  f"{c}_{num}"

    def get_resource(self):
        return self._main_widget.get_resource()

    def set_resource(self, resource):
        self._main_widget.set_resource(resource)

    def set_title(self, title):
        self._main_widget.set_title(title)

    def on_delete(self):
        self.contaner.delete_item(self)

    def get_index(self):
        return self.contaner.items.index(self)

    def set_changed_callback(self, callback):
        self._main_widget.set_changed_callback(callback)


class ArrayResourceInput(ResourceInputWidget):
    IdCounter = 0

    def __init__(self, bound_resource_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bound_resource_class = bound_resource_class
        self.items = []
        #self.resource = bound_resource_class([])
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self.label = QLabel()
        self._layout.addWidget(self.label)
        self.add_btn = QPushButton()
        self.add_btn.setText("+")
        self.add_btn.clicked.connect(self.on_add_item)
        self._layout.addWidget(self.add_btn)
        self.widget_identifier = self.IdCounter
        type(self).IdCounter += 1

    def on_add_item(self):
        self.add_item()
        self.name_items()
        self.trigger_callback()

    def add_item(self):
        index_to_insert = len(self.items) + 1
        item = ArrayItemWidget(self.bound_resource_class.InnerType, self)
        self.items.append(item)
        self._layout.insertWidget(index_to_insert, item)
        item.set_changed_callback(self.trigger_callback)
        return item

    def name_items(self):
        for i, item in enumerate(self.items):
            label = self.bound_resource_class.ITEM_LABEL.format(i)
            item.set_title(label)

    def delete_item(self, item):
        if item in self.items:
            item.setParent(None)
            self._layout.removeWidget(item)
            item.set_changed_callback(None)

            self.items.remove(item)
            self.name_items()
            self.trigger_callback()

    def clear_items(self):
        for item in self.items:
            self._layout.removeWidget(item)
            item.deleteLater()
            item.setParent(None)
        self.items.clear()

    def get_resource(self):
        data = [item.get_resource() for item in self.items]
        return self.bound_resource_class(data)

    def set_resource(self, resource):
        self.clear_items()
        for subresource in resource.data:
            item = self.add_item()
            item.set_resource(subresource)
        self.name_items()

    def set_title(self, title):
        self.label.setText(title)

    def swap_items(self, i1, i2):
        if i1 < 0 or i1 >= len(self.items):
            return
        if i2 < 0 or i2 >= len(self.items):
            return
        if i1 == i2:
            return
        tmp1 = self.items[i1].get_resource()
        tmp2 = self.items[i2].get_resource()
        self.items[i1].set_resource(tmp2)
        self.items[i2].set_resource(tmp1)
        self.trigger_callback()


class ArrayResource(Resource, ResourceInput, ResourceOutput):
    InnerType: type[Resource] = BlankResource
    InputWidget = ArrayResourceInput
    ITEM_LABEL = "Item #{}"

    def __init__(self, data: list):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __len__(self):
        return len(self.data)

    def append(self,item):
        self.data.append(item)

    def pop(self,key):
        return self.data.pop(key)

    def insert(self, index, obj):
        self.data.insert(index, obj)


    def __repr__(self):
        return f"{type(self).__name__}({self.data})"

    @classmethod
    def create_widget(cls, *args, **kwargs):
        return cls.InputWidget(cls, *args, **kwargs)

    @classmethod
    def input_is_available(cls):
        return issubclass(cls.InnerType, ResourceInput) and cls.InnerType.input_is_available()

    @classmethod
    def output_is_available(cls):
        return issubclass(cls.InnerType, ResourceOutput) and cls.InnerType.output_is_available()

    def serialize(self):
        return [item.serialize() for item in self.data]

    @classmethod
    def deserialize(cls, data):
        data = [cls.InnerType.deserialize(item) for item in data]
        return cls(data)

    def unwrap(self):
        return [item.unwrap() for item in self.data]

    @classmethod
    def try_from(cls, x):
        if isinstance(x, list):
            if len(x) == 0:
                return cls([])
            else:
                data = []
                for item in x:
                    if isinstance(item, cls.InnerType):  # If item is already an InnerType
                        new_item = item
                    else:
                        new_item = cls.InnerType.try_from(item)
                    if new_item is None:  # If item failed to convert
                        return None
                    data.append(new_item)
                return cls(data)


    def show_data(self, label:str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout()
        w.setLayout(l)

        title = QLabel()
        title.setText(label)
        l.addWidget(title)
        for i,item in enumerate(self.data):
            if isinstance(item,ResourceOutput):
                l.addWidget(item.show_data(self.ITEM_LABEL.format(i)))
        return w