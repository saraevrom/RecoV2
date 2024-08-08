import numpy as np
import json
from typing import Dict, Type

from PyQt6.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PyQt6.QtWidgets import QApplication
from PyQt6 import QtCore
from RecoResources import ResourceInput, Resource, ResourceInputWidget, ResourceOutput
from RecoResources.strict_functions import Default


class ArrayDisplay(QWidget):
    def __init__(self, label, value, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.value = value
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(QLabel(label))
        layout.addWidget(QLabel(f"Shape: {self.value.shape}"))

        # non_editable_line_edit = QLineEdit(str(self.value.shape))
        # non_editable_line_edit.setReadOnly(True)
        disp = self.value
        if len(disp.shape) == 1:
            disp = disp.reshape((disp.shape[0], 1))
        if len(disp.shape) == 2:
            rows, columns = disp.shape
            table_widget = QTableWidget()
            table_widget.setColumnCount(columns)
            table_widget.setRowCount(rows)
            table_widget.setMinimumHeight(400)
            for i in range(disp.shape[0]):
                for j in range(disp.shape[1]):
                    item = QTableWidgetItem(f"{disp[i, j]}")
                    table_widget.setItem(i, j, item)

            layout.addWidget(table_widget)
            self.table = table_widget
        self.clip = QApplication.clipboard()

    def keyPressEvent(self, e):
        if e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier:
            selected = self.table.selectedRanges()

            if e.key() == QtCore.Qt.Key.Key_C:  # copy
                # s = "\t".join([str(self.table.horizontalHeaderItem(i).text()) for i in
                #                range(selected[0].leftColumn(), selected[0].rightColumn() + 1)
                #                if self.table.horizontalHeaderItem(i)])
                # s = s + '\n'
                s = ""

                for r in range(selected[0].topRow(), selected[0].bottomRow() + 1):
                    # s += self.table.verticalHeaderItem(r).text() + '\t'
                    for c in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                        try:
                            s += str(self.table.item(r, c).text()) + "\t"
                        except AttributeError:
                            s += "\t"
                    s = s[:-1] + "\n"  # eliminate last '\t'
                self.clip.setText(s)


class NumpyArrayResource(Resource, ResourceOutput):
    def __init__(self, value: np.ndarray):
        self.value = value

    def serialize(self):
        return self.value.tolist()

    @classmethod
    def deserialize(cls, data):
        return cls(np.array(data))

    def unwrap(self):
        return self.value

    @classmethod
    def try_from(cls, x):
        if isinstance(x, np.ndarray):
            return cls(x)
        return None

    def show_data(self, label: str) -> QWidget:
        return ArrayDisplay(label, self.value)
