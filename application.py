import copy
import os.path
import traceback
from multiprocessing import Process, Queue, Pipe
from typing import Optional, Type
import shutil
import inspect
import json, tempfile

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget, QMainWindow, QPushButton, QMenu, QTabWidget, QHBoxLayout, QScrollArea, QVBoxLayout
from PyQt6.QtCore import QSize, QRunnable, pyqtSlot, pyqtSignal, QObject, QThreadPool, QThread, QTimer
from RecoResources import ResourceForm, ResourceDisplay, ResourceStorage, ResourceRequest, ScriptResource, Resource
from reconstruction_model import ReconsructionModel
from RecoResources import DisplayList
from button_list import ButtonPanel
import workspace

from scene import Drawer

import matplotlib, sys
matplotlib.use('Qt5Agg')

SCRIPT_KEY = "SCRIPT"
BASEDIR = os.path.dirname(os.path.realpath("__file__"))
STOCK_SRCDIR = os.path.join(BASEDIR,"stock_models")
STOCK_COMMONS_SRCDIR = os.path.join(BASEDIR,"stock_commons")

class RecoResourcesBundle(object):
    def __init__(self,resource_storage:ResourceStorage,request:Optional[ResourceRequest],runner:Optional[Type[ReconsructionModel]]=None, display_list:Optional[DisplayList]=None):
        self.resource_storage = resource_storage
        self.request = request
        self.runner = runner
        self.display_list = display_list

    def __getstate__(self):
        return self.serialize()

    def __setstate__(self, state):
        newstate = self.deserialize(state)
        if newstate is None:
            raise RuntimeError("Cannot deserialize reco resources")
        self.__dict = newstate.__dict__

    @staticmethod
    def default():
        return RecoResourcesBundle(ResourceStorage(), None)

    def sync_outputs(self, outputs:ResourceDisplay):
        if self.runner is None:
            base = dict()
        else:
            base = self.runner().AdditionalLabels.copy()
            #print("RUNNER BASE",base,self.runner,self.runner.AdditionalLabels,self.runner.RequestedResources.labels())

        if self.request is not None:
            #print(self.request.labels())
            base.update(self.request.labels())
            #print("LABELS",base)
        outputs.show_resources(self.resource_storage, base, allow_list=self.display_list)

    def sync_inputs(self, inputs:ResourceForm):
        inputs.populate_resources(self.request)

    @staticmethod
    def open_new_model():
        item = RecoResourcesBundle.default()
        success = item.update_script()
        print("success:",success)
        return item, success

    def update_script(self):
        script = ScriptResource.try_load()
        print("SCRIPT",script)
        if script is None:
            return False
        self._load_script(script)
        return True

    def _load_script(self,script):

        # storage = self.resource_storage
        globs = {
            "__builtins__": __builtins__
        }
        script.run_script(globs)
        for k in globs.keys():
            v = globs[k]
            if inspect.isclass(v) and (v is not ReconsructionModel) and issubclass(v, ReconsructionModel):
                print("Found model", v.__name__)
                request = v.RequestedResources
                if self.request is None or request.is_compatible_with(self.request):
                    print("Script set")
                    #self.resource_storage = storage
                    self.request = request
                    self.display_list = v.DisplayList
                    self.runner = v
                    self.resource_storage.set_resource(SCRIPT_KEY, script)

    def run_model(self):
        if self.runner is None:
            return
        self.runner.calculate(self.resource_storage)

    def get_actions(self):
        if self.runner is None:
            return dict()
        return self.runner.get_actions()

    def save(self,path):
        resources = self.resource_storage.serialize()
        with open(path,"w") as fp:
            json.dump(resources,fp)

    def serialize(self):
        return self.resource_storage.serialize()


    @staticmethod
    def from_resources(resources:ResourceStorage):
        if not resources.has_resource(SCRIPT_KEY):
            return
        script = resources.get_resource(SCRIPT_KEY)
        res = RecoResourcesBundle.default()
        res.resource_storage = resources
        res._load_script(script)
        return res

    @staticmethod
    def deserialize(data):
        resources = ResourceStorage.deserialize(data)
        return RecoResourcesBundle.from_resources(resources)


    @staticmethod
    def open(path):
        with open(path,"r") as fp:
            data = json.load(fp)
        resources = ResourceStorage.deserialize(data)
        return RecoResourcesBundle.from_resources(resources)


def add_action(parent,menu,name,func,shortcut=None):
    action = QAction(name, parent)
    if shortcut is not None:
        action.setShortcut(shortcut)
    action.triggered.connect(func)
    menu.addAction(action)


def add_modules_dir(s):
    sys.path.insert(0,s)
    for file in os.listdir(s):
        if file.endswith(".py"):
            modname = file[:-3]
            try:
                mod = __import__(modname)
                print(f"Loading {modname} OK")
                print(dir(mod))
            except:
                print(f"Loading {modname} failed")
    Resource.index_subclasses(True)


class Worker(Process):
    def __init__(self, state, tx):
        super().__init__()
        self.tx = tx
        self.resources = RecoResourcesBundle.deserialize(state)

    def run(self):
        try:
            self.resources.run_model()
            print("Model run is done")
            ser = self.resources.serialize()
            #print("Ser",ser)
            (fd,path) = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as f:
                f.write(json.dumps(ser))
            self.tx.send(path)
            print("Job is done")
        except:
            print("ERROR ocurred")
            traceback.print_exc()



class WorkerHandler(object):
    def __init__(self,resources:RecoResourcesBundle):
        conn1,conn2 = Pipe()
        self.worker = Worker(resources.serialize(),conn2)
        self.rx = conn1
        self.worker.start()
        self.result = None

    def check_result(self):
        if self.worker.is_alive():
            return 0,None
        else:
            print("Worker is finished. Joining...")
            self.worker.join()
            print("Worker is finished. Joined")
            if self.rx.poll():
                path = self.rx.recv()
                with open(path) as f:
                    dat = json.load(f)
                os.remove(path)
                return 1, RecoResourcesBundle.deserialize(dat)
            else:
                return 1, None

    def interrupt(self):
        if self.worker.is_alive():
            self.worker.terminate()


class PADAMOReco(QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        workspace.Workspace.initialize_workspace(self)
        self.setWindowTitle("PADAMO-RECO")
        self.setMinimumSize(900,600)

        menu_bar = self.menuBar()
        file_menu = QMenu("&File",self)
        menu_bar.addMenu(file_menu)

        add_action(self,file_menu,"Open python script as model",self.on_bootstrap_model, shortcut="Ctrl+Shift+O")
        add_action(self,file_menu,"Open model",self.on_open_model, shortcut="Ctrl+O")
        add_action(self,file_menu,"Save model",self.on_save_model, shortcut="Ctrl+S")
        add_action(self,file_menu,"Update script",self.on_update_script)
        file_menu.addSeparator()
        add_action(self,file_menu,"Copy models to workspace",self.on_copy_models)

        # SETTINGS
        settings_menu = QMenu("&Settings", self)
        menu_bar.addMenu(settings_menu)

        add_action(self,settings_menu,"Change workspace", self.on_setup_workspace)

        widget = QWidget()
        main_layout = QHBoxLayout()
        widget.setLayout(main_layout)



        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        self.output_tab = ResourceDisplay(placeholder="No outputs")
        scroll = QScrollArea()
        scroll.setWidget(self.output_tab)
        scroll.setWidgetResizable(True)

        tabs.addTab(scroll, "Output")

        self.plotter = Drawer()
        tabs.addTab(self.plotter, "Scene")

        right_panel = QWidget()
        self.right_panel_data = QVBoxLayout()
        right_panel.setLayout(self.right_panel_data)

        main_layout.addWidget(right_panel)
        right_panel.setFixedWidth(600)

        self.setCentralWidget(widget)
        self.resources = RecoResourcesBundle.default()
        self.action_list = ButtonPanel()
        self.right_panel_data.addWidget(self.action_list)

        self.add_action("Pull data",self.on_dry_run)
        self.add_action("Reconstruct",self.on_run)
        self.add_action("Stop reconstruction",self.on_stop)

        #self.right_panel_data.addStretch()
        self.inputs_panel = ResourceForm(placeholder="No inputs")
        scroll0 = QScrollArea()
        scroll0.setWidget(self.inputs_panel)
        scroll0.setWidgetResizable(True)
        self.right_panel_data.addWidget(scroll0)
        self._sync_resources()

        if workspace.Workspace.has_dir():
            print("Workspace is set. Using workspace commons")
            ws = workspace.Workspace("reco_commons")
            ws.ensure_directory()
            add_modules_dir(ws.get_tgt_dir())
        else:
            print("No workspace is set. Using local commons")
            add_modules_dir(STOCK_COMMONS_SRCDIR)
        self.plotter.replot_hook = self.replot_hook
        self.plotter.event_sync_hook = self.event_sync_hook

        self.worker = None
        self.worker_timer = QTimer()
        self.worker_timer.timeout.connect(self.monitor_worker)
        self.worker_timer.start(1000)

    def on_dry_run(self):
        self._pull_inputs()
        self._sync_outputs()
        self.on_plotter_notify()

    def add_action(self,name,func):
        btn = QPushButton(name)
        btn.clicked.connect(func)
        self.right_panel_data.addWidget(btn)

    def _refresh_actions(self):
        actions = self.resources.get_actions()
        self.action_list.clear()
        print("AVAILABLE ACTIONS",actions)
        for (label,action) in actions.values():
            self.action_list.add_action(label, action)

    def _pull_inputs(self):
        inputs = self.inputs_panel.get_resources()
        #print("PULL",inputs.resources)
        self.resources.resource_storage.update_with(inputs)

    def _push_resources(self):
        self.inputs_panel.set_resources(self.resources.resource_storage)

    def _sync_resources(self):
        self.resources.sync_inputs(self.inputs_panel)
        self.resources.sync_outputs(self.output_tab)
        #self.resources.sync_data(self.inputs_panel, self.output_tab)

    def on_setup_workspace(self):
        workspace.Workspace.initialize_workspace(self, force=True)

    def _sync_inputs(self):
        self.resources.sync_inputs(self.inputs_panel)
        #self.inputs_panel.set_resources()

    def _sync_outputs(self):
        self.resources.sync_outputs(self.output_tab)

    def on_bootstrap_model(self):
        resources,success = RecoResourcesBundle.open_new_model()
        if not success:
            return
        self.resources = resources
        print(self.resources.resource_storage.resources)
        self._sync_inputs()
        self._pull_inputs()
        self._sync_outputs()
        self._refresh_actions()
        self.on_plotter_notify()
        #self._sync_resources()
        #workspace.Workspace("reco_models").get_open_file_name()

    def on_update_script(self):
        if self.resources.resource_storage.has_resource(SCRIPT_KEY):
            try:
                self.resources.update_script()
                self._sync_inputs()
                self._push_resources()
                self._sync_outputs()
                self._refresh_actions()
                self.on_plotter_notify()
            except:
                print(traceback.format_exc())

    def on_open_model(self):
        path = workspace.Workspace("reconstructions").get_open_file_name(caption="Open saved reconstruction",
                                                                         filter="Model data (*.json)")[0]
        if path:
            self.resources = RecoResourcesBundle.open(path)
            self._sync_inputs()
            self._push_resources()
            self._sync_outputs()
            self._refresh_actions()
            self.on_plotter_notify()


    def on_save_model(self):
        path = workspace.Workspace("reconstructions").get_save_file_name(caption="Open saved reconstruction",
                                                                         filter="Model data (*.json)")[0]
        if path:
            self._pull_inputs()
            self.resources.save(path)


    def on_copy_models(self):
        if workspace.Workspace.has_dir():
            tgtdir = workspace.Workspace(ScriptResource.Workspace)(".")
            print("TGT DIR", tgtdir)
            for file in os.listdir(STOCK_SRCDIR):
                srcfile = os.path.join(STOCK_SRCDIR,file)
                shutil.copy(srcfile,tgtdir)


            #stock_commons
            tgtdir = workspace.Workspace("reco_commons")(".")
            print("COMMONS TGT DIR", tgtdir)
            for file in os.listdir(STOCK_COMMONS_SRCDIR):
                srcfile = os.path.join(STOCK_COMMONS_SRCDIR, file)
                shutil.copy(srcfile, tgtdir)

    def _run_parallel(self):
        try:
            self.resources.run_model()
        except Exception:
            print(traceback.format_exc())

    def on_run(self):
        self._pull_inputs()
        if self.worker is None:
            self.worker = WorkerHandler(self.resources)

    def monitor_worker(self):
        if self.worker is not None:
            self.worker:WorkerHandler
            status,res = self.worker.check_result()
            if status == 1:
                print("Worker returned finishing status")
                self.worker = None
                if res is not None:
                    self.resources = res
                    self.update_outputs()
                    print("Reco OK")


    def update_outputs(self):
        self.resources.sync_outputs(self.output_tab)
        self.on_plotter_notify()

    def on_plotter_notify(self):
        self.plotter.notify(self.resources)

    def replot_hook(self):
        #self._push_resources()
        self._pull_inputs()

    def event_sync_hook(self):
        self._push_resources()

    def on_stop(self):
        if self.worker is not None:
            self.worker.interrupt()
