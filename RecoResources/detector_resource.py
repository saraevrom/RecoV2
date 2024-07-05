import json

import numpy as np
from PyQt6.QtWidgets import QVBoxLayout, QDialog, QWidget, QHBoxLayout, QPushButton
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

from RecoResources.file_content_resource import FileLoadedResource, FileLoadedResourceInput, FileContentWrapper
from padamo_rs_detector_parser import PadamoDetector





class DetectorPixelSelector(QDialog):
    def __init__(self,detector:PadamoDetector,*args,**kwargs):
        super().__init__(*args,**kwargs)
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.detector = detector
        self.alive_pixels = np.array(detector.alive_pixels)

        self.fig = Figure()
        self.ax = self.fig.add_subplot()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect("button_press_event",self.on_plot_click)
        layout.addWidget(self.canvas,1)

        toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(toolbar,0)

        actions = QWidget()
        actions_layout = QHBoxLayout()
        actions.setLayout(actions_layout)

        rst = QPushButton("Reset")
        rst.clicked.connect(self.reset_selection)
        actions_layout.addWidget(rst,1)

        invert = QPushButton("Invert")
        invert.clicked.connect(self.invert_selection)
        actions_layout.addWidget(invert, 1)

        layout.addWidget(actions,0)

        bottom = QWidget()
        bottom_layout = QHBoxLayout()
        bottom.setLayout(bottom_layout)
        ok = QPushButton("OK")
        ok.clicked.connect(self.on_ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.on_cancel)
        bottom_layout.addWidget(ok)
        bottom_layout.addWidget(cancel)

        layout.addWidget(bottom,0)
        self.redraw()

    def reset_selection(self):
        self.alive_pixels = np.full(self.detector.compat_shape,True)
        self.redraw()

    def invert_selection(self):
        self.alive_pixels = np.logical_not(self.alive_pixels)
        self.redraw()

    def redraw(self):
        self.ax.clear()
        lx,mx,ly,my = self.detector.draw_blank(self.ax, alive_override=self.alive_pixels)
        self.ax.set_xlim(lx,mx)
        self.ax.set_ylim(ly,my)
        self.ax.set_aspect("equal")
        self.canvas.draw()

    def on_plot_click(self,event):
        if event.button==1:
            #xy = event.xydata
            i = self.detector.index_at(np.array([event.xdata,event.ydata]))
            if i is not None:
                self.alive_pixels[i] = not self.alive_pixels[i]
                self.redraw()

    def on_ok(self):
        self.detector.alive_pixels = self.alive_pixels
        self.close()

    def on_cancel(self):
        self.close()


class DetectorWrapper(FileContentWrapper):
    def __init__(self,value:PadamoDetector):
        self.value = value

    @classmethod
    def from_str(cls, str_value):
        value = PadamoDetector(json.loads(str_value))
        return cls(value)

    def serialize(self):
        return {
            "detector":self.value.json_data,
            "alive_pixels": self.value.alive_pixels.tolist()
        }

    @classmethod
    def deserialize(cls, v):
        detector = PadamoDetector(v["detector"])
        detector.alive_pixels = np.array(v["alive_pixels"])
        return cls(detector)

    def unwrap(self):
        return self.value


class DetectorResourceInput(FileLoadedResourceInput):
    def __init__(self, refclass, *args, **kwargs):
        super().__init__(refclass,*args,**kwargs)
        btn = QPushButton("Mask pixels")
        btn.clicked.connect(self.on_select_active_pixels)
        self._layout.addWidget(btn)

    def on_select_active_pixels(self):
        if self.content is not None and self.content.unwrap() is not None:
            dialog = DetectorPixelSelector(self.content.unwrap())
            dialog.exec()



class DetectorResource(FileLoadedResource):
    InputWidget = DetectorResourceInput
    Workspace = "detectors"
    DialogCaption = "Open PADAMO-RS detector"
    Filter = "Detector data (*.json)"
    WrapperClass = DetectorWrapper

    def get_detector(self):
        if self.value is not None:
            return self.value.unwrap()

    def unwrap(self):
        return self.get_detector()
