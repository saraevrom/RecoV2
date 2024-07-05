from PyQt6.QtWidgets import QWidget, QPushButton, QVBoxLayout



class ButtonPanel(QWidget):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

    def clear(self):
        for i in reversed(range(self._layout.count())):
            self._layout.itemAt(i).widget().setParent(None)

    def add_action(self,label, action):
        btn = QPushButton(label)
        self._layout.addWidget(btn)
        btn.clicked.connect(action)
