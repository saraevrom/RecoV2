import tempfile, shutil, base64

# STRIP IMPORTS
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QCheckBox, QPushButton
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QIntValidator
from PyQt6 import QtCore
from RecoResources.resource_output import ResourceOutput

from arviz.data.inference_data import InferenceData
import arviz as az

from RecoResources import Resource

az.rcParams['data.load'] = 'eager'


# STRIP CLASS
class TraceDisplay(QWidget):
    def __init__(self,label,trace,*args,**kwargs):
        super().__init__(*args,**kwargs)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.trace = trace
        self.label = label
        layout.addWidget(QLabel(label))

        self.is_robust_check = QCheckBox("robust")
        self.is_robust_check.checkStateChanged.connect(self.update_table)
        self.layout().addWidget(self.is_robust_check)

        self.round_to_editor = QLineEdit()
        self.round_to_editor.setText("3")
        self.round_to_editor.setValidator(QIntValidator())
        self.last_round_to = 3
        self.layout().addWidget(self.round_to_editor)
        self.round_to_editor.textEdited.connect(self.on_roundto_edit)

        btn = QPushButton("Plot trace")
        btn.clicked.connect(self.plot_trace)
        layout.addWidget(btn)

        btn = QPushButton("Plot pair")
        btn.clicked.connect(self.plot_pair)
        layout.addWidget(btn)

        self.table_widget = QTableWidget()
        layout.addWidget(self.table_widget)
        self.table_widget.setMinimumHeight(400)

        self.update_table()

    def on_roundto_edit(self):
        try:
            new_round = int(self.round_to_editor.text())
            if new_round>0:
                # print(new_round)
                self.last_round_to = new_round
        except ValueError:
            pass
        self.update_table()

    def update_table(self):
        self.table_widget.clear()
        if self.is_robust_check.isChecked():
            summary = az.summary(self.trace.posterior,stat_focus="median",round_to=self.last_round_to)
        else:
            summary = az.summary(self.trace.posterior,round_to=self.last_round_to)

        #print(type(summary),summary)

        keys = list(summary.keys())
        columns = len(keys)+1
        rows = len(summary)+1
        self.table_widget.setColumnCount(columns)
        self.table_widget.setRowCount(rows)
        #print(keys,columns)
        for j in range(1,columns):
            item = QTableWidgetItem(keys[j-1])
            item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
            self.table_widget.setItem(0, j, item)

        for i in range(1,rows):
            for j in range(columns):
                if j == 0:
                    item = QTableWidgetItem(summary.index[i-1])
                    item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(QtCore.Qt.CheckState.Checked)
                    self.table_widget.setItem(i, j, item)
                else:
                    key = keys[j-1]
                    item = QTableWidgetItem(str(summary[key].iloc[i-1]))
                    item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled)
                    self.table_widget.setItem(i, j, item)

    def get_vars(self):
        #columns = self.table_widget.columnCount()
        rows = self.table_widget.rowCount()
        res = []
        for i in range(1,rows):
            item = self.table_widget.item(i, 0)
            check = item.checkState()
            if check is QtCore.Qt.CheckState.Checked:
                res.append(item.text())
        return res

    def plot_trace(self):
        vars = self.get_vars()
        axs = az.plot_trace(self.trace,vars).flatten()
        fig = axs[0].get_figure()
        fig.canvas.manager.set_window_title(self.label)
        for ax in axs:
            fig = ax.get_figure()
            fig.tight_layout()
        fig = axs[0].get_figure()
        fig.show()

    def plot_pair(self):
        vars = self.get_vars()
        axs = az.plot_pair(self.trace,var_names=vars)
        if hasattr(axs,"flatten"):
            axs = axs.flatten()
            fig = axs[0].get_figure()
            fig.canvas.manager.set_window_title(self.label)
            for ax in axs:
                fig = ax.get_figure()
                if fig is not None:
                    fig.tight_layout()
            fig = axs[0].get_figure()
            fig.show()
        else:
            ax = axs
            fig = ax.get_figure()
            fig.canvas.manager.set_window_title(self.label)
            fig.tight_layout()
            fig.show()


# STRIP SUPERCLASSES EXCEPT Resource
class TraceResource(Resource, ResourceOutput):
    def __init__(self,trace:InferenceData):
        self.trace = trace

    def serialize(self):
        tempdir = tempfile.mkdtemp()
        tgt_file = tempdir+"/data.nc"
        self.trace.to_netcdf(tgt_file,compress=True)
        with open(tgt_file,"rb") as fp:
            data = fp.read()
        shutil.rmtree(tempdir)
        return base64.b64encode(data).decode("ascii")

    @classmethod
    def deserialize(cls,data):
        tempdir = tempfile.mkdtemp()
        tgt_file = tempdir+"/data.nc"
        with open(tgt_file,"wb") as fp:
            decoded = base64.b64decode(data.encode("ascii"))
            fp.write(decoded)
        trace = InferenceData.from_netcdf(tgt_file)
        shutil.rmtree(tempdir)
        return cls(trace)

    def unwrap(self):
        return self.trace

    @classmethod
    def try_from(cls, x):
        if isinstance(x, InferenceData):
            return cls(x)
        return None

    # STRIP
    def show_data(self, label:str) -> QWidget:
        return TraceDisplay(label,self.trace)
    # END
