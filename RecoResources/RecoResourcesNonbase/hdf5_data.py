import io, base64

import h5py
import numpy as np

# STRIP IMPORTS
from PyQt6.QtWidgets import QLabel, QPushButton, QHBoxLayout, QDialog, QTreeWidget, QTreeWidgetItem
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QMessageBox

from RecoResources import Resource

# STRIP IMPORTS
from RecoResources import ResourceInput, ResourceInputWidget, ResourceOutput
import workspace

# STRIP CLASS
class TreeItem(QTreeWidgetItem):
    def __init__(self,main,path):
        super().__init__(main)
        self.path = path

# STRIP
def populate_tree(tree,view,path=""):
    for k in view.keys():
        v = view[k]
        item = TreeItem(tree,path+"/"+k)
        item.setText(0, k)
        if hasattr(v,"keys"):
            item.setText(1, "Group")
            populate_tree(item,v,item.path)
        else:
            item.setText(1,f"Shape: {v.shape}")
# END


# STRIP CLASS
class HDF5ViewDialog(QDialog):
    def __init__(self,filename,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.file_desc = h5py.File(filename)
        self.setModal(True)
        self.show()
        self.result_field = None
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.label = QLabel("")
        layout.addWidget(self.label)

        self.tree = QTreeWidget()
        layout.addWidget(self.tree)
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Field","Info"])
        populate_tree(self.tree,self.file_desc)
        self.tree.doubleClicked.connect(self.on_selection_changed)

        bottom = QWidget()
        bottom_layout = QHBoxLayout()
        bottom.setLayout(bottom_layout)
        ok = QPushButton("OK")
        ok.clicked.connect(self.on_ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.on_cancel)
        bottom_layout.addWidget(ok)
        bottom_layout.addWidget(cancel)

        layout.addWidget(bottom)

    def on_ok(self):
        if self.result_field is None:
            QMessageBox.warning(self,"Field selection", "Field is not selected. Double click needed field")
        else:
            self.close()

    def on_cancel(self):
        self.result_field = None
        self.close()

    def on_selection_changed(self):
        items = self.tree.selectedItems()
        if items:
            item = items[0].path
            if not hasattr(self.file_desc[item],"keys"):
                self.result_field = item
                self.label.setText(item)

    @classmethod
    def ask_field(cls,filename):
        dialog = HDF5ViewDialog(filename)
        dialog.exec()
        return dialog.result_field


# STRIP CLASS
class HDF5ResourceInput(ResourceInputWidget):
    def __init__(self, refclass, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.content = None
        self._shape_show = ""
        self._title = ""
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)
        self._label = QLabel()
        self._layout.addWidget(self._label)
        self.refclass = refclass

        btn = QPushButton("Pick file")
        self._layout.addWidget(btn)
        btn.clicked.connect(self.on_load_data)

    def on_load_data(self):

        data = self.refclass.try_load_data()
        if data is not None:
            self._set_content(data)
            self.trigger_callback()

    def _update_title(self):
        if self._shape_show:
            self._label.setText(f"{self._title} {self._shape_show}")
        else:
            self._label.setText(self._title)

    def set_title(self,title):
        self._title = title
        self._update_title()

    def get_resource(self):
        if self.content is None:
            return HDF5Resource(None)
        else:
            return HDF5Resource(self.content)

    def _set_content(self,content):
        self.content = content
        if content is None:
            self._shape_show = ""
        else:
            self._shape_show = str(content.shape)
        self._update_title()

    def set_resource(self,resource):
        self._set_content(resource.value)


# STRIP SUPERCLASSES EXCEPT Resource
class HDF5Resource(Resource,ResourceInput, ResourceOutput):
    # STRIP
    InputWidget = HDF5ResourceInput
    DialogCaption = "Open HDF5 file"
    Filter = "HDF5 data (*.h5)"

    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(cls)
    # END

    def __init__(self,value):
        self.value = value

    def set_value(self, value):
        self.value = value

    # STRIP
    def resetable(self):
        return True

    def reset(self):
        self.set_value(np.array([0.0]))
    # END

    def __repr__(self):
        return f"{type(self).__name__}=({self.value})"

    def serialize(self):
        if self.value is None:
            return None
        compressed_array = io.BytesIO()
        np.savez_compressed(compressed_array, self.value)
        compressed_array.seek(0)
        bytes_array = compressed_array.read()
        return base64.b64encode(bytes_array).decode('ascii')

    @classmethod
    def deserialize(cls,data):
        if data is None:
            return cls(None)
        bytes_array = base64.b64decode(data.encode('ascii'))
        compressed_array = io.BytesIO()
        compressed_array.write(bytes_array)
        compressed_array.seek(0)
        arr = np.load(compressed_array)["arr_0"]
        return cls(arr)

    def unwrap(self):
        return self.value

    # STRIP
    @classmethod
    def ask_filename(cls):
        kwargs = dict(caption=cls.DialogCaption,filter=cls.Filter)
        asked, _ = workspace.Workspace(".").get_open_file_name(**kwargs)
        return asked

    @classmethod
    def try_load_data(cls):
        asked = cls.ask_filename()
        if not asked:
            return None
        field = HDF5ViewDialog.ask_field(asked)
        if not field:
            return None
        with h5py.File(asked) as fp:
            data = np.array(fp[field])
            return data

    def show_data(self, label:str) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout()
        w.setLayout(layout)

        layout.addWidget(QLabel(label))
        if self.value is None:
            layout.addWidget(QLabel("No data"))
        else:
            layout.addWidget(QLabel(f"Data {self.value.shape}"))
        return w
    # END