from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout

class ActionWrapper(object):
    def __init__(self, a1, a2):
        self.a1 = a1
        self.a2 = a2

    def __call__(self, *args, **kwargs):
        self.a1()
        self.a2()

class ButtonPanel(QWidget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        self.action_hook = None

    def on_action_ocurred(self):
        if self.action_hook:
            self.action_hook()

    def clear(self):
        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().setParent(None)

    def add_action(self,label, action):
        btn = QPushButton(label)
        self._layout.addWidget(btn)
        action_wrapper = ActionWrapper(self.on_action_ocurred,action)
        btn.clicked.connect(action_wrapper)
