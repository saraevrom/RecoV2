# STRIP
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QWidget

from RecoResources import Resource

# STRIP IMPORTS
from RecoResources.resource_output import ResourceOutput
from RecoResources.resource_input import ResourceInput, ResourceInputWidget
from RecoResources.strict_functions import Default

from stars import StarList, Star


# STRIP CLASS
class StarListInput(ResourceInputWidget):
    def __init__(self,ref,*args,**kwargs):
        self.ref = ref
        super().__init__(*args,**kwargs)
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.label = QLabel("")
        layout.addWidget(self.label)
        self.entry = QLineEdit()
        self._default_stylesheet = self.entry.styleSheet()
        self.last_data = ref.default()
        self.entry.textChanged.connect(self._validate)
        layout.addWidget(self.entry)

    def set_title(self,title):
        self.label.setText(title)

    def _validate(self):
        starlist = StarList.from_str(self.entry.text())
        if starlist is not None:
            self.last_data = self.ref(starlist)
            self.entry.setStyleSheet(self._default_stylesheet)
            self.trigger_callback()
        else:
            self.entry.setStyleSheet("color: red;")

    def set_resource(self,resource):
        ids = [star.get_star_identifier() for star in resource.starlist]
        s = " ".join(ids)
        self.entry.setText(s)
        self._validate()

    def get_resource(self):
        return self.last_data


# STRIP SUPERCLASSES EXCEPT Resource
class StarListResource(Resource,ResourceInput,Default,ResourceOutput):

    # STRIP
    InputWidget = StarListInput

    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(cls,*args,**kwargs)

    # END

    def __init__(self, starlist:StarList):
        self.starlist = starlist

    def serialize(self):
        return [star.hr for star in self.starlist]

    @classmethod
    def deserialize(cls,data):
        # if isinstance(data,str):
        #     return cls(StarList.from_str(data))
        starlist = StarList.new_empty()
        for hr in data:
            starlist.append(Star.fetch_hr(hr))
        return cls(starlist)

    # STRIP
    @classmethod
    def default(cls):
        return cls(StarList.new_empty())
    # END

    def unwrap(self):
        return self.starlist

    @classmethod
    def try_from(cls, x):
        if isinstance(x, StarList):
            return cls(x)

    # STRIP
    def show_data(self, label:str) -> QWidget:
        qw = QWidget()
        layout = QVBoxLayout()
        qw.setLayout(layout)
        layout.addWidget(QLabel(label))
        for i,star in enumerate(self.starlist.stars):
            layout.addWidget(QLabel(f"Star {i}\t{star.get_star_identifier()}"))

        return qw
    # END
