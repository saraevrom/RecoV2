from RecoResources.resource import ResourceStorage,Resource
from RecoResources.resource_input import ResourceInput, ResourceInputWidget, ResourceForm, ResourceRequest
from RecoResources.resource_output import ResourceOutput, ResourceDisplay, DisplayList

# Base resources
from RecoResources.basic_resources import IntegerResource, FloatResource, StringResource, BooleanResource, BlankResource
from RecoResources.basic_resources import ChoiceResource
from RecoResources.alternate_resource import AlternatingResource,ResourceVariant
from RecoResources.strict_functions import StrictFunction
from RecoResources.combine_resources import CombineResource
from RecoResources.option_resource import OptionResource

# Auxiliary resources
from RecoResources.prior_resource import DistributionResource
from RecoResources.file_content_resource import FileLoadedResource
from RecoResources.script_resource import ScriptResource
from RecoResources.hdf5_data import HDF5Resource
from RecoResources.pymc_trace import TraceResource
from RecoResources.detector_resource import DetectorResource
from RecoResources.time_resource import TimeResource
from RecoResources.star_list_resource import StarListResource


if __name__=="__main__":
    from PyQt6.QtWidgets import QMainWindow, QApplication, QHBoxLayout, QWidget, QScrollArea, QPushButton
    import sys

    @StrictFunction(int)
    def makes_integer():
        return 42

    @StrictFunction(str)
    def makes_string():
        return "YOLO"

    class BlankTest(BlankResource):
        Label = "This is an unchangeable constant value"

    # @StrictFunction(BlankTest)
    # def makes_blank():
    #     return BlankTest()


    @StrictFunction(bool)
    def makes_bool():
        return False

    class TestAlternatorResource(AlternatingResource):
        Variants = [
            ResourceVariant(makes_integer, "Variant 1"),
            ResourceVariant(makes_string, "Variant 2"),
            ResourceVariant(makes_bool, "Variant 3"),
            ResourceVariant(BlankTest, "Blank")
        ]

    class TestSubform(CombineResource):
        Fields = ResourceRequest({
            "A":dict(display_name="Field A",default_value="AAAA"),
            "B":dict(display_name="Field B",default_value=645),
        })


    class CyclicSubform(CombineResource):
        Fields = ResourceRequest({
            "getdistractedlol": dict(display_name="A distracting field",default_value="AAAA")
        })

    class SimpleChoice(ChoiceResource):
        Choices = {
            "eggs":"Eggs",
            "bacon":"Bacon",
            "spam":"Spam",
        }

    class TestOption(OptionResource):
        OptionType = IntegerResource

    requests = ResourceRequest()
    requests.add_request("name",display_name="Name", default_value="John Doe")
    requests.add_request("choice",display_name="Food of choice", type_=SimpleChoice, default_value="spam")
    requests.add_request("age",display_name="Age", default_value=42)
    requests.add_request("weight",display_name="Weight", default_value=85.0)
    requests.add_request("o_rly",display_name="O RLY?", default_value=True)
    requests.add_request("add_a_file",display_name="This is a file", type_=FileLoadedResource)
    requests.add_request("variant_test",display_name="Alternative test",type_=TestAlternatorResource)
    requests.add_request("subform", display_name="Subform", type_=TestSubform)
    requests.add_request("ok_option", TestOption, display_name="Test option")
    requests.add_request("distribution_test", DistributionResource, "A distribution")
    requests.add_request("hdf5", HDF5Resource, "A H5 data")

    simpler_requests = ResourceRequest()

    simpler_requests.add_request("x0", DistributionResource, "X0")
    simpler_requests.add_request("y0", DistributionResource, "Y0")

    class TestApp(QMainWindow):
        def __init__(self, *args, **kwargs):
            super().__init__(*args,**kwargs)
            self.setWindowTitle("A wild resource thing appeared")
            self.output = ResourceDisplay()

            btn = QPushButton("Read")
            btn.clicked.connect(self.on_clicked)

            btn1 = QPushButton("Change form")
            btn1.clicked.connect(self.on_flip)

            inputs = ResourceForm()
            inputs.populate_resources(requests)

            box = QWidget()
            layout = QHBoxLayout()
            box.setLayout(layout)

            scroll0 = QScrollArea()
            scroll0.setWidget(self.output)
            scroll0.setWidgetResizable(True)
            layout.addWidget(scroll0)
            layout.addWidget(btn)
            layout.addWidget(btn1)

            scroll = QScrollArea()
            scroll.setWidget(inputs)
            scroll.setWidgetResizable(True)
            layout.addWidget(scroll)
            self.resource_form = inputs
            self.requests = requests

            self.setCentralWidget(box)

        def on_clicked(self):
            res = self.resource_form.get_resources()
            ser_res = res.serialize()
            print(ser_res)
            deser_res = ResourceStorage.deserialize(ser_res)
            print(deser_res.resources)
            self.output.show_resources(deser_res,self.requests.labels())

        def on_flip(self):
            self.requests = simpler_requests
            self.resource_form.populate_resources(self.requests)



    app = QApplication(sys.argv)
    main_window = TestApp()
    main_window.show()
    app.exec()