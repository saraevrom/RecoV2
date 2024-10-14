import re
from RecoResources import FileLoadedResource

INCLUDE_REGEX = re.compile(r"^\s*#\s*INCLUDE\s*([^\n]+)")

class ScriptResource(FileLoadedResource):
    Workspace = "reco_models"
    DialogCaption = "Choose script"
    Filter = "Python script (*.py)"
    BinaryMode = False

    def run_script(self, globals_=None):
        if globals_ is None:
            globals_ = dict()
        if self.value is not None:
            #print("Script", self.value.unwrap())
            exec(self.value.unwrap(),globals_)

    def get_includes(self):
        if self.value is None:
            return []
        src = self.value.unwrap()
        data = []
        for line in src.split("\n"):
            mat = INCLUDE_REGEX.match(line)
            if mat:
                data.append(mat.groups()[0])
        return data
