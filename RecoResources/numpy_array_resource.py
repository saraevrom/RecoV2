import numpy as np
import json
from typing import Dict, Type

from PyQt6.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem

from RecoResources import ResourceInput, Resource, ResourceInputWidget, ResourceOutput
from RecoResources.strict_functions import Default

class NumpyArrayResource(Resource, ResourceOutput):
    def __init__(self,value:np.ndarray):
        self.value = value

    def serialize(self):
        return self.value.tolist()

    @classmethod
    def deserialize(cls,data):
        return cls(np.array(data))

    def unwrap(self):
        return self.value

    @classmethod
    def try_from(cls, x):
        if isinstance(x, np.ndarray):
            return cls(x)
        return None

    def show_data(self, label:str) ->QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        layout.addWidget(QLabel(label))
        layout.addWidget(QLabel(f"Shape: {self.value.shape}"))

        # non_editable_line_edit = QLineEdit(str(self.value.shape))
        # non_editable_line_edit.setReadOnly(True)
        disp = self.value
        if len(disp.shape)==1:
            disp = disp.reshape((disp.shape[0],1))
        if len(disp.shape)==2:
            rows,columns = disp.shape
            table_widget = QTableWidget()
            table_widget.setColumnCount(columns)
            table_widget.setRowCount(rows)
            table_widget.setMinimumHeight(400)
            for i in range(disp.shape[0]):
                for j in range(disp.shape[1]):
                    item = QTableWidgetItem(f"{disp[i,j]}")
                    table_widget.setItem(i, j, item)

            layout.addWidget(table_widget)
        return widget
