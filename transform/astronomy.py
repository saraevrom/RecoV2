from .vectors import Vector3, Quaternion
from .transform import Transform, TransformBuilder
import numpy as np


'''
Abbreviations:
ECEF: Earth-Centered Earth-Fixed frame
    Origin -- center of earth
    X - lies in a plane of equator, extending to the prime meridian.
    Z - aligned with Earth rotation axis
    Y - chosen to make XYZ left-handed coordinate system
OCEF: Observer-Centered Earth-Fixed frame
    Origin -- observer
    Z - points to zenith
    X - points to east
    Y - points to north
ECI: Earth-Centered Inertial frame
    Origin -- center of earth
    X - points to vernal equinox. 
    Z - aligned with Earth rotation axis
    Y - chosen to make XYZ left-handed coordinate system
ERA: Earth rotation angle 
WGS: World Geodetic System
'''

WGS_84_SEMIMAJOR_AXIS_KM = 6378.137
WGS_84_INVERSE_FLATTENING = 298.257223563
WGS_84_SEMIMINOR_AXIS_KM = (1-1/WGS_84_INVERSE_FLATTENING)*WGS_84_SEMIMAJOR_AXIS_KM
WGS_84_SQR_ECCENTRICITY = 1-(1-1/WGS_84_INVERSE_FLATTENING)**2


def latlon_to_ecef_position(lat:float, lon:float,elevation=0.0,backend=np):
    '''
    Transforms latitude, longitude, elevation into geodetic cartesian coordinates
    :param lat: latitude in radians
    :param lon: longitude in radians
    :param elevation: elevation in km
    :param backend: functions backend
    :return: Cartesian coordinates as vector3
    '''
    a = WGS_84_SEMIMAJOR_AXIS_KM
    b = WGS_84_SEMIMINOR_AXIS_KM
    h = elevation

    n = a**2/((a*backend.cos(lat))**2+(b*backend.sin(lat))**2)**0.5
    x = (n+h)*backend.cos(lat)*backend.sin(lon)
    y = (n+h)*backend.cos(lat)*backend.cos(lon)
    z = ((b/a)**2*n+h)*backend.sin(lat)
    return Vector3(x,y,z)


def ecef_align(lat:float, lon:float, own_rotation=0.0,backend=np)->Quaternion:
    '''
    Makes rotation pointed to zenith at given latitude and longitude in ECEF.
    Axes will be aligned to OCEF and rotated along OCEF axis z with own rotation
    :param lat: observer latitude
    :param lon: longitude
    :param own_rotation: rotation around Z axis in OCEF
    :param backend: functions backend
    :return: rotation to zenith in ECEF
    '''
    longitude_rotator = Quaternion.rotate_xy(lon,backend=backend)
    latitude_rotator = Quaternion.rotate_xz(lat,backend=backend)
    own_rotator = Quaternion.rotate_yz(own_rotation,backend=backend)
    swapper = Quaternion.from_axis_rotation(2*np.pi/3,Vector3.ones().normalized(),backend=backend)
    return longitude_rotator*latitude_rotator*own_rotator*swapper


def unixtime_to_era(unixtime):
    '''
    Converts unix time to earth rotation angle
    :param unixtime: unix time, UTC
    :return:
    '''
    ut1 = unixtime / 86400.0 - 10957.5
    return np.pi * 2 * (0.7790572732640 + 1.00273781191135448 * ut1) % (2 * np.pi)


def observatory_transform(lat:float, lon:float,elevation=0.0,apply_position=True,backend=np):
    '''
    Creates transform with local axes aligned according to OCEF.
    :param lat: object latitude
    :param lon: object longitude
    :param elevation: object elevation
    :param apply_position: Apply position on ellipsoid
    :param backend: calculation backend
    :return:
    '''
    rotation = ecef_align(lat,lon,backend=backend)
    builder = TransformBuilder().with_rotation(rotation)
    if apply_position:
        position = latlon_to_ecef_position(lat, lon, elevation, backend=backend)
        builder.with_position(position)
    return builder.build()
