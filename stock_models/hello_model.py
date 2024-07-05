from reco_prelude import ResourceStorage,ReconsructionModel,ResourceRequest, LabelledAction


class HelloModel(ReconsructionModel):
    '''
    This is a test model
    Not yet probabilistic
    But it can test app
    '''
    RequestedResources = ResourceRequest({
        "a": dict(display_name="A", default_value=2),
        "b": dict(display_name="B", default_value=2),
    })

    AdditionalLabels = {
        "result": "Result",
    }

    @classmethod
    def calculate(cls, resources:ResourceStorage):
        a = resources.get("a")
        b = resources.get("b")
        result_value = a+b
        resources.set("result", result_value)

    @LabelledAction("Print hello")
    @staticmethod
    def print_hello(resources):
        print("HELLO!!!")
    