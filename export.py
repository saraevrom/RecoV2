import os.path, json
from pathlib import Path

from PyQt6.QtWidgets import QDialog, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QCheckBox, QScrollArea, QLabel

from typing import Optional

from ResourcePatcher import copy_obj
from RecoResources import ResourceStorage, Resource
from RecoResources import ScriptBundleResource

ADDITIONAL_PACKAGES = '''
transform
stars
padamo_rs_detector_parser.py
quadrature_xy_small.txt
quadrature_w_small.txt
quadrature_xy.txt
quadrature_w.txt
'''.strip().split("\n")

BASE_DIR = Path(os.path.abspath(os.path.dirname(os.path.realpath(__file__))))

def clone_data(resources: ResourceStorage):
    return ResourceStorage.deserialize(resources.serialize())


def export_model(model:ResourceStorage, tgt_path:str, reset_keys, additional_pkgs):
    print("Exporting model to", tgt_path)
    tgt = Path(tgt_path)
    tgt.mkdir(parents=True,exist_ok=True)

    model = clone_data(model)
    for k in model.resources.keys():
        res: Resource = model.get_resource(k)
        if res.resetable() and k in reset_keys:
            res.reset()
        if res.identifier() == ScriptBundleResource.identifier() and hasattr(res,"strip_source"):
            res.strip_source()

    with tgt.joinpath("model.json").open("w") as fp:
        json.dump(model.serialize(), fp)

    copy_obj("RecoResources", tgt.joinpath("RecoResources"), ["__pycache__"])
    # copy_obj("stars", tgt.joinpath("stars"), ["__pycache__"])
    # copy_obj("transform", tgt.joinpath("transform"), ["__pycache__"])
    additional_pkgs.append("reconstruction_model.py")
    additional_pkgs.append("reco_resources_bundle.py")
    for add_pkg in additional_pkgs:
        copy_obj(BASE_DIR.joinpath(add_pkg),tgt.joinpath(add_pkg), ["__pycache__"])
    copy_obj("reco_template.py", tgt.joinpath("main_example.py"))


class Checklist(QWidget):
    def __init__(self, title, checklist_keys:list[str], checklist_init:Optional[dict[str,bool]],
                 default_value:bool, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QVBoxLayout()
        self.setLayout(layout)

        layout.addWidget(QLabel(text=title))

        self.checkboxes = dict()
        for key in checklist_keys:
            if checklist_init is not None and key in checklist_init.keys():
                check = checklist_init[key]
            else:
                check = default_value
            self.checkboxes[key] = QCheckBox(text=key)
            self.checkboxes[key].setChecked(check)
            layout.addWidget(self.checkboxes[key])


    def get_checks(self) -> dict[str, bool]:
        res = dict()
        for key in self.checkboxes.keys():
            res[key] = self.checkboxes[key]
        return res

class Exporter(QDialog):
    LastPkgChecklist = None
    LastResetChecklist = None

    def __init__(self, resources: ResourceStorage, target_directory:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resources = resources
        self.target_directory = target_directory
        layout = QVBoxLayout()
        self.setLayout(layout)

        top = QWidget()
        top_layout = QHBoxLayout()
        top.setLayout(top_layout)

        pkg_scroll_area = QScrollArea()
        self.pkg_selector = Checklist("Packages", ADDITIONAL_PACKAGES, self.LastPkgChecklist,True)
        pkg_scroll_area.setWidget(self.pkg_selector)
        top_layout.addWidget(pkg_scroll_area)

        var_scroll_area = QScrollArea()
        self.var_selector = Checklist("Reset variables", self.resources.get_resetables(),
                                      self.LastResetChecklist,False)
        var_scroll_area.setWidget(self.var_selector)
        top_layout.addWidget(var_scroll_area)

        layout.addWidget(top)


        bottom = QWidget()
        bottom_layout = QHBoxLayout()
        bottom.setLayout(bottom_layout)
        ok = QPushButton("OK")
        ok.clicked.connect(self.on_ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.on_cancel)
        bottom_layout.addWidget(ok)
        bottom_layout.addWidget(cancel)

        layout.addWidget(bottom, 0)

    def on_ok(self):
        self.LastPkgChecklist = self.pkg_selector.get_checks()
        self.LastResetChecklist = self.var_selector.get_checks()
        resets = [k for k in self.LastResetChecklist.keys() if self.LastResetChecklist[k]]
        pkgs = [k for k in self.LastPkgChecklist.keys() if self.LastPkgChecklist[k]]
        export_model(self.resources, self.target_directory, resets, pkgs)
        self.close()

    def on_cancel(self):
        self.close()
