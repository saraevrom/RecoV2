# STRIP
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QDateTimeEdit, QWidget, QLineEdit

from datetime import datetime, timezone

from RecoResources import Resource

# STRIP IMPORTS
from RecoResources.resource_output import ResourceOutput
from RecoResources.resource_input import ResourceInput, ResourceInputWidget
from RecoResources.strict_functions import Default

UTC = timezone.utc


# STRIP CLASS
class TimeInput(ResourceInputWidget):
    def __init__(self,ref,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.ref = ref
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.label = QLabel("")
        layout.addWidget(self.label)
        self.dt_selector = QDateTimeEdit()
        self.set_resource(ref.default())
        self.dt_selector.dateTimeChanged.connect(self.on_datetime_change)
        #self.dt_selector.change
        layout.addWidget(self.dt_selector)

    def on_datetime_change(self):
        self.trigger_callback()

    def set_title(self,title):
        self.label.setText(title)

    def get_resource(self):
        qd = self.dt_selector.dateTime()
        #qd.setTimeZone(QTimeZone.utc(),QDateTime.TransitionResolution.Reject)
        dt = qd.toPyDateTime()
        dt = dt.replace(tzinfo=UTC)
        #print(str(dt),repr(dt),dt.tzinfo)
        return self.ref(dt)

    def set_resource(self,resource):
        self.dt_selector.setDateTime(resource.dt)


# STRIP SUPERCLASSES EXCEPT Resource
class TimeResource(Default, Resource, ResourceInput, ResourceOutput):
    # STRIP
    InputWidget = TimeInput

    def __init__(self, dt: datetime):
        self.dt = dt

    # STRIP
    @classmethod
    def create_widget(cls,*args,**kwargs):
        return cls.InputWidget(cls,*args,**kwargs)

    @classmethod
    def default(cls):
        return cls(datetime.now(UTC))
    # END

    def serialize(self):
        return self.dt.timestamp()

    @classmethod
    def deserialize(cls,data):
        return cls(datetime.fromtimestamp(data,UTC))

    # STRIP
    def show_data(self, label:str) ->QWidget:
        w = QWidget()
        layout = QHBoxLayout()
        w.setLayout(layout)
        layout.addWidget(QLabel(label))

        non_editable_line_edit = QLineEdit(str(self.dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")))
        non_editable_line_edit.setReadOnly(True)

        layout.addWidget(non_editable_line_edit)

        return w
    # END

    def unwrap(self):
        return self.dt

    @classmethod
    def try_from(cls, x):
        if isinstance(x, datetime):
            return cls(x)
