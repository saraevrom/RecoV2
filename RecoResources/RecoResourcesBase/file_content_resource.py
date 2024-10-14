from typing import Optional, Type, Any
import sys

# STRIP
from PyQt6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QFileDialog

from RecoResources import Resource

# STRIP IMPORTS
from RecoResources import ResourceInput, ResourceInputWidget
import workspace


# STRIP CLASS
class FileLoadedResourceInput(ResourceInputWidget):
    def __init__(self, refclass, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = refclass(None)
        self._bytes_display = ""
        self._title = ""
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)
        self._label = QLabel()
        self._layout.addWidget(self._label)
        self.refclass = refclass

        btn = QPushButton("Pick file")
        self._layout.addWidget(btn)
        btn.clicked.connect(self.on_load_data)


    @staticmethod
    def format_info(resource):
        return str(sys.getsizeof(resource)) + " bytes"

    def on_load_data(self):
        content = self.refclass.try_load()
        if content is not None:
            self.set_resource(content)
            self.trigger_callback()

    def _update_title(self):
        if self._bytes_display:
            self._label.setText(f"{self._title} ({self._bytes_display})")
        else:
            self._label.setText(self._title)

    def set_title(self,title):
        self._title = title
        self._update_title()

    def get_resource(self):
        return self.content

    def set_resource(self,resource):
        self.content = resource
        self._bytes_display = self.format_info(resource)
        self._update_title()
        #


class FileContentWrapper(object):
    @classmethod
    def from_str(cls,str_value):
        raise NotImplementedError

    def serialize(self):
        raise NotImplementedError

    @classmethod
    def deserialize(cls, v):
        raise NotImplementedError

    def unwrap(self):
        raise NotImplementedError


class StringWrapper(FileContentWrapper):
    def __init__(self,str_value):
        self.value = str_value

    @classmethod
    def from_str(cls,str_value):
        return cls(str_value)

    def serialize(self):
        return self.value

    @classmethod
    def deserialize(cls, v):
        #print(v)
        return cls(v)

    def unwrap(self):
        return self.value


# STRIP SUPERCLASSES EXCEPT Resource
class FileLoadedResource(Resource,ResourceInput):
    # STRIP
    InputWidget = FileLoadedResourceInput
    Workspace:Optional[str] = None
    DialogCaption = "Open file"
    Filter = "Any (*.*)"
    BinaryMode = False
    # END
    WrapperClass:Type[FileContentWrapper] = StringWrapper

    def __init__(self,value):
        self.value = value

    # STRIP
    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(cls)
    # END

    @classmethod
    def from_str(cls,s):
        return cls(cls.WrapperClass.from_str(s))

    def __repr__(self):
        return f"{type(self).__name__}=({self.value})"

    def serialize(self):
        if self.value is None:
            return None
        return self.value.serialize()

    @classmethod
    def deserialize(cls,data):
        if data is None:
            return cls(None)
        v = cls.WrapperClass.deserialize(data)
        return cls(v)

    def unwrap(self):
        if self.value is None:
            return None
        return self.value.unwrap()

    # STRIP
    @classmethod
    def ask_filename(cls)->Optional[str]:
        kwargs = dict(caption=cls.DialogCaption,filter=cls.Filter)
        if cls.Workspace is None:
            asked, _ = QFileDialog.getOpenFileName(**kwargs)
        else:
            asked, _ = workspace.Workspace(cls.Workspace).get_open_file_name(**kwargs)
        return asked

    @classmethod
    def try_load(cls)->Optional[Any]:
        asked = cls.ask_filename()
        print("Loading",asked)
        if asked:
            if cls.BinaryMode:
                mode = "rb"
            else:
                mode = "r"
            with open(asked, mode) as fp:
                return cls.from_str(fp.read())
        return None
    # END

