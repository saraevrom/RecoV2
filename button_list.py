from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout



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

        def action_wrapper():
            self.on_action_ocurred()
            action()
        btn.clicked.connect(action_wrapper)
