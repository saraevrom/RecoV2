import traceback

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


from RecoResources import ResourceStorage


SCRIPT_KEY = "SCRIPT"
class Drawer(QWidget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.fig = Figure()
        self.ax = self.fig.add_subplot()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect("button_press_event",self.on_click)
        self.canvas.mpl_connect("motion_notify_event",self.on_click)
        layout.addWidget(self.canvas)

        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)

        self.scene_selector = QComboBox()
        layout.addWidget(self.scene_selector)
        self.scene_selector.setVisible(False)

        self.runner = None
        self.storage = None
        self.selector_visible = False
        self.scene_selector.currentIndexChanged.connect(self.replot)
        self.replot_hook = None
        self.event_sync_hook = None
        self._last_variant = None
        self._settings_storage = dict()

    def notify(self, storage):
        from application import RecoResourcesBundle
        storage:RecoResourcesBundle
        print(storage.runner, storage.resource_storage)
        if storage.runner is not self.runner:
            self.runner = storage.runner
            if storage.runner is not None:
                self.set_variants(storage.runner.get_scene_names())
            print("Scene: Runner set")
        if storage.resource_storage is not self.storage:
            self.storage = storage.resource_storage
            print("Scene: Resource set")
        print(self.storage, self.runner)
        self.replot()

    def set_variants(self, variants):
        if variants is None or not variants:
            self.scene_selector.setVisible(False)
            self.selector_visible = False
        else:
            self.selector_visible = True
            self.scene_selector.clear()
            self.scene_selector.setVisible(True)
            for var in variants:
                self.scene_selector.addItem(var)
            self.scene_selector.setCurrentIndex(0)
            print(self.scene_selector.currentText())

    def get_variant(self):
        if self.selector_visible:
            key = self.scene_selector.currentText()
            return key
        return None

    def clear_plot(self):
        self.ax.clear()

    def commit(self):
        self.canvas.draw()
        #print("Plot redrawn")

    def replot(self):
        if self.replot_hook:
            self.replot_hook()
        if self.runner is not None and self.storage is not None:
            #print("Replotting...")
            if self._last_variant is not None:
                print("Remembering view", self._last_variant)
                x_vi = self.ax.xaxis.get_view_interval()
                y_vi = self.ax.yaxis.get_view_interval()
                xlim = self.ax.get_xlim()
                ylim = self.ax.get_ylim()
                self._settings_storage[self._last_variant] = x_vi, y_vi, xlim, ylim
            self.clear_plot()
            var = self.get_variant()
            try:
                self.runner.draw_scene(self.storage, self.fig,self.ax, var)
                self._last_variant = var
            except Exception: # Explicit silence
                print(traceback.format_exc())
                self.clear_plot()
            if var in self._settings_storage.keys():
                x_vi, y_vi, xlim, ylim = self._settings_storage[var]
                self.ax.set_xlim(*xlim)
                self.ax.set_ylim(*ylim)
                self.ax.xaxis.set_view_interval(*x_vi)
                self.ax.yaxis.set_view_interval(*y_vi)
            self.commit()
        else:
            print("No runner")

    def allow_callbacks(self):
        res = not self.toolbar.mode.strip()
        return res

    def clear_zooms(self):
        self._settings_storage.clear()
        self._last_variant = None

    def on_click(self,event):
        if self.runner is not None and self.storage is not None and self.allow_callbacks():
            try:
                #print("entered",self.get_variant())
                replot_res = self.runner.on_scene_mouse_event(self.storage,event,self.get_variant())
                if replot_res:
                    if self.event_sync_hook is not None:
                        self.event_sync_hook()
                    self.replot()
            except Exception: # Explicit silence
                print(traceback.format_exc())
                self.replot()
        #print(event)


