import numpy as np

from .astronomy import latlon_to_ecef_position, unixtime_to_era, observatory_transform, ecef_align
from .transform import Transform, TransformBuilder
from .vectors import Vector2, Vector3, Quaternion, Vector4
from .matrices import Matrix

def simple_projection_matrix() -> Matrix:
    '''
    A primitive projection matrix
    :return: 4x4 primitive projection matrix
    '''
    m = Matrix.identity(4)
    m.swap_rows(2,3)
    #m[2], m[3] = m[3], m[2]
    return m


def scale_matrix(sx: float, sy: float, sz: float)-> Matrix:
    '''
    Scale homogenous matrix
    :param sx: scale factor x
    :param sy: scale factor y
    :param sz: scale factor z
    :return: 4x4 scale matrix
    '''
    return Matrix.diagonal([sx, sy, sz, 1.0])


def projection_matrix(f: float)-> Matrix:
    '''
    :param f: focal distance
    :return: 4x4 matrix that also scales x and y by f
    '''
    m = simple_projection_matrix()
    return scale_matrix(f, f, 1.0) @ m
