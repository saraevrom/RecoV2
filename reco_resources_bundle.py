from typing import Optional, Type
import inspect
import json
import gc, os

# STRIP
from RecoResources import ResourceForm, ResourceDisplay

from RecoResources import ResourceRequest

from RecoResources import ScriptResource, Resource, ResourceStorage
from reconstruction_model import ReconsructionModel
from RecoResources import DisplayList

# STRIP
import workspace

SCRIPT_KEY = "SCRIPT"

# STRIP
BASEDIR = os.path.dirname(os.path.realpath("__file__"))
STOCK_SRCDIR = os.path.join(BASEDIR,"stock_models")
STOCK_COMMONS_SRCDIR = os.path.join(BASEDIR,"stock_commons")
# END

class ActionWrapper(object):
    def __init__(self, callable, resources_provider):
        self.callable = callable
        self.resources_provider = resources_provider

    def __call__(self, *args, **kwargs):
        self.callable(self.resources_provider.resource_storage,*args,**kwargs)


class RecoResourcesBundle(object):
    def __init__(self,resource_storage:ResourceStorage,request:Optional[ResourceRequest],
                 runner:Optional[Type[ReconsructionModel]]=None, display_list:Optional[DisplayList]=None):
        self.resource_storage = resource_storage
        self.request = request
        self.runner = runner
        self.display_list = display_list

        # STRIP
        if workspace.Workspace.has_dir():
            print("Workspace is set. Using workspace commons")
            ws = workspace.Workspace("reco_commons")
            ws.ensure_directory()
            # add_modules_dir()
            self.additional_modules = ws.get_tgt_dir()
        else:
            print("No workspace is set. Using local commons")
            # add_modules_dir(STOCK_COMMONS_SRCDIR)
            self.additional_modules = STOCK_COMMONS_SRCDIR
        # END
        self._actions = None

    # STRIP
    def __getstate__(self):
        return self.serialize()

    def __setstate__(self, state):
        newstate = self.deserialize(state)
        if newstate is None:
            raise RuntimeError("Cannot deserialize reco resources")
        self.__dict = newstate.__dict__

    # END

    @staticmethod
    def default():
        return RecoResourcesBundle(ResourceStorage(), None)

    # STRIP
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
        #print("success:",success)
        return item, success

    def update_script(self):
        script = ScriptResource.try_load()
        #print("SCRIPT",script)
        if script is None:
            return False
        self._update_includes(script)
        self._load_script(script)
        return True

    def update_except_script(self, donor_path):
        if not self.resource_storage.has_resource(SCRIPT_KEY):
            return
        with open(donor_path,"r") as fp:
            data = json.load(fp)
        resources = ResourceStorage.deserialize(data)
        self.resource_storage.update_with(resources,[SCRIPT_KEY])
        self.execute()
    # END

    def execute(self):
        if not self.resource_storage.has_resource(SCRIPT_KEY):
            return
        script = self.resource_storage.get_resource(SCRIPT_KEY)
        self._update_includes(script)
        self._load_script(script)

    def _update_includes(self, script):
        from RecoResources.RecoResourcesCore import ScriptBundleResource
        modules = script.get_includes()
        keys = list(self.resource_storage.resources.keys())
        for key in keys:
            if key.startswith("RESOURCE_BUNDLE_"):
                self.resource_storage.delete_resource(key)

        print("MODULES", modules)
        for name in modules:
            print("Including module",name)
            res = ScriptBundleResource.from_singlefile_module_name(name, [self.additional_modules])
            self.resource_storage.set_resource(f"RESOURCE_BUNDLE_{name}", res)

    def _load_script(self,script):

        # storage = self.resource_storage
        globs = {
            "__builtins__": __builtins__
        }
        self.resource_storage.load_bundles()
        Resource.index_subclasses(True)
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
                    Resource.index_subclasses(True)
                    self.resource_storage.try_load_partial_resources()
                    gc.collect(0)

    def run_model(self):
        if self.runner is None:
            return
        self.runner.calculate(self.resource_storage)

    def get_actions(self):
        if self.runner is None:
            return dict()
        actions = self.runner.get_actions()
        for k in actions.keys():
            label = actions[k][0]
            action0 = actions[k][1]
            # def action(*args):
            #     return action0(self.resource_storage)
            print("Got action",k, label,action0)
            action = ActionWrapper(action0,self)
            actions[k] = label, action
        return actions

    def run_action(self, key):
        if self._actions is None:
            self._actions = self.get_actions()
        return self._actions[key][1]()

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

# STRIP
# REPLACE
#     def __getattr__(self, item):
#         return getattr(self.resource_storage,item)
# END