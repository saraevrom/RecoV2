import numpy as np
from typing import Dict, Type

from PyQt6.QtWidgets import QLabel, QLineEdit, QHBoxLayout, QCheckBox, QWidget, QComboBox
from RecoResources import ResourceInput, Resource, ResourceInputWidget, ResourceOutput
from RecoResources.strict_functions import Default

class ArrayResource(Resource):
    def