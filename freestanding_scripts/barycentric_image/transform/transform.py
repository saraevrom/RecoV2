from typing import Optional, Any

import numpy as np

from .vectors import Vector3,Quaternion
from .matrices import Matrix


class Transform(object):
    def __init__(self,position:Vector3,rotation:Quaternion, parent: Optional[Any] = None):
        self.position = position
        self.rotation = rotation
        self.parent = parent

    def local_model_matrix(self) -> Matrix:
        rot = self.rotation.to_mat4()
        pos = self.position.to_mat4()
        return pos @ rot

    def local_view_matrix(self) -> Matrix:
        inv_rot = self.rotation.conj().to_mat4()
        inv_pos = (-self.position).to_mat4()
        return inv_rot @ inv_pos

    def model_matrix(self):
        m = self.local_model_matrix()
        if self.parent is not None:
            m = self.parent.model_matrix() @ m
        return m

    def view_matrix(self):
        v = self.local_view_matrix()
        if self.parent is not None:
            v = v @ self.parent.view_matrix()
        return v


class TransformBuilder(object):
    def __init__(self):
        self.position = Vector3.zero()
        self.rotation = Quaternion.identity()
        self.parent = None

    def with_position(self, pos:Vector3):
        self.position = pos
        return self

    def with_rotation(self, rot:Quaternion):
        self.rotation = rot
        return self

    def with_parent(self,parent:Transform):
        self.parent = parent
        return self

    def build(self) -> Transform:
        return Transform(position=self.position,rotation=self.rotation,parent=self.parent)
