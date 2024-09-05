from typing import Type, Dict, Union, Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFrame, QSizePolicy, QLabel, QTabWidget, QScrollArea
from RecoResources.resource import Resource, ResourceStorage


class FocusingTabWidget(QTabWidget):
    def focusInEvent(self, a0):
        super().focusInEvent(a0)
        crt_widget = self.currentWidget()
        if crt_widget:
            crt_widget.setFocus()

class ResourceInputWidget(QWidget):
    def set_changed_callback(self, callback):
        setattr(self, "changed_callback", callback)

    def trigger_callback(self):
        if hasattr(self, "changed_callback"):
            self.changed_callback()

    def get_resource(self):
        raise NotImplementedError

    def set_resource(self,resource):
        raise NotImplementedError

    def set_title(self,title):
        raise NotImplementedError


class ResourceInput(object):
    InputWidget: Type[ResourceInputWidget] = None

    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(*args,**kwargs)

class SingleResourceRequest(object):
    def __init__(self, type_:Optional[Type[Union[Resource,ResourceInput]]]=None,
                 display_name:Optional[str]=None, default_value:Optional[Resource]=None,category="Main"):
        from RecoResources.basic_resources import remap_basic_values
        if type_ is None and default_value is None:
            raise ValueError("at least type_ or default_value must be specified")
        self.default_value = remap_basic_values(default_value)
        if type_ is None:
            type_ = type(self.default_value)
        self.type = type_
        self.display_name = display_name
        self.category = category



class ResourceRequest(object):
    def __init__(self,requests_input:Optional[dict]=None):
        self.requests = dict()
        if requests_input is not None:
            for k in requests_input.keys():
                v = requests_input[k]
                if isinstance(v,list) or isinstance(v,tuple):
                    self.add_request(k,*v)
                elif isinstance(v,dict):
                    self.add_request(k, **v)


    def is_compatible_with(self, base):
        base_keys = set(base.requests.keys())
        self_keys = set(self.requests.keys())
        return base_keys.issubset(self_keys)


    def add_request(self,key:str,type_:Optional[Type[Union[Resource,ResourceInput]]]=None,
                    display_name:Optional[str]=None,
                    default_value:Optional[Union[Resource,int,float,str,bool]]=None,
                    category="Main"):
        self.requests[key] = SingleResourceRequest(type_,display_name,default_value,category=category)

    def labels(self):
        return {k:self.requests[k].display_name for k in self.requests.keys() if self.requests[k].display_name is not None}

    def get_instantiatable(self):
        request = ResourceRequest()
        requests = {k:self.requests[k] for k in self.requests.keys() if self.requests[k].default_value is not None}
        request.requests = requests
        return request

class ResourceForm(QWidget):
    def __init__(self,requested_resources:Optional[ResourceRequest]=None, placeholder="Inputs",
                 categorize=False, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.categorize = categorize

        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self.requested_resources = ResourceRequest()
        self.source_widgets = dict()

        if categorize:
            self._notebook = FocusingTabWidget()
            self._notebook.currentChanged.connect(self.on_tab_switch)
            self._layout.addWidget(self._notebook)
            self._tabs = dict()
        else:
            self._tabs = None
            self._notebook = None

        if requested_resources is not None:
            self.populate_resources(requested_resources)

        self._enabled_callback = True

        #self._layout.addWidget(QLabel(placeholder))
        #self._placeholder = placeholder

        self.changed_callback = None

    def on_tab_switch(self):
        print("Tab switched")
        self._notebook:QTabWidget
        self._notebook.setFocus()

    def _clear_tabs(self):
        self._notebook.clear()
        self._tabs = dict()

    def _get_tab(self, name):
        if name not in self._tabs.keys():
            v = QWidget()
            l = QVBoxLayout()

            scroll0 = QScrollArea()
            scroll0.setWidget(v)
            scroll0.setWidgetResizable(True)

            v.setLayout(l)
            self._notebook.addTab(scroll0, name)
            self._tabs[name] = l
        return self._tabs[name]

    def populate_resources(self, requested_resources:Optional[ResourceRequest]):

        if self.categorize:
            self._clear_tabs()
            self.source_widgets = dict()
        else:
            for i in reversed(range(self._layout.count())):
                self._layout.itemAt(i).widget().setParent(None)

        # if requested_resources is None or not self.requested_resources:
        #     self._layout.addWidget(QLabel(self._placeholder))

        if requested_resources is None:
            self.requested_resources = None
            #self._layout.addStretch()
            return

        self.requested_resources = requested_resources.requests

        for resource_key in self.requested_resources.keys():
            resource_request = self.requested_resources[resource_key]
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame_layout = QVBoxLayout()
            frame_layout.setContentsMargins(0,0,0,0)
            frame.setLayout(frame_layout)
            widget = resource_request.type.create_widget()
            frame_layout.addWidget(widget,1)

            if resource_request.display_name is None:
                widget.set_title(f"Resource: {resource_key}")
            else:
                widget.set_title(resource_request.display_name)

            if resource_request.default_value is not None:
                widget.set_resource(resource_request.default_value)
            widget.set_changed_callback(self.on_data_changed)
            #
            if self.categorize:
                tab = self._get_tab(resource_request.category)
                tab.addWidget(frame)
            else:
                self._layout.addWidget(frame)
            self.source_widgets[resource_key] = widget

        #self._layout.addStretch()

    def get_resources(self) -> ResourceStorage:
        self._enabled_callback = False
        resources = ResourceStorage()
        for widget_key in self.source_widgets.keys():
            resources.set_resource(widget_key, self.source_widgets[widget_key].get_resource())
        self._enabled_callback = True
        return resources

    def set_resources(self, storage:ResourceStorage):
        self._enabled_callback = False
        widget_keys = set(self.source_widgets.keys())
        storage_keys = set(storage.resources.keys())
        keys = widget_keys.intersection(storage_keys)
        for k in keys:
            self.source_widgets[k].set_resource(storage.get_resource(k))
        self._enabled_callback = True


    def on_data_changed(self):
        print("Change triggered")
        if self.changed_callback and self._enabled_callback:
            self.changed_callback()
