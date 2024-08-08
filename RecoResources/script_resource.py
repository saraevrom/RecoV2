from RecoResources.file_content_resource import FileLoadedResource


class ScriptResource(FileLoadedResource):
    Workspace = "reco_models"
    DialogCaption = "Choose script"
    Filter = "Python script (*.py)"
    BinaryMode = False

    def run_script(self, globals_=None):
        if globals_ is None:
            globals_ = dict()
        #
        if self.value is not None:
            #print("Script", self.value.unwrap())
            exec(self.value.unwrap(),globals_)