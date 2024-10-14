import numpy as np
import pytensor.tensor

from RecoResources import CombineResource, AlternatingResource, ResourceRequest, ResourceVariant
from RecoResources.RecoResourcesShipped.prior_resource import template_normal, DistributionResource
from transform import Quaternion
from transform.astronomy import ecef_align


def equatorial(dec,ha,rot):
    if isinstance(dec, float):
        backend = np
    else:
        backend = pytensor.tensor
    return ecef_align(dec,ha,rot,backend)


def local_data(elevation, azimuth, rot):
    if isinstance(elevation, float):
        backend = np
    else:
        backend = pytensor.tensor
    own_rot = Quaternion.rotate_zx(rot,backend)
    az_rot = Quaternion.rotate_yx(azimuth,backend)
    elev_rot = Quaternion.rotate_yz(elevation,backend)
    return az_rot*elev_rot*own_rot


class Orientation(object):
    def get_rotation(self, extractor,local:Quaternion,prefix):
        raise NotImplementedError

    def get_rotation_estimation(self,local:Quaternion,prefix):
        return self.get_rotation(extract_estimation,local,prefix)

    def get_prior(self,local:Quaternion,prefix):
        return self.get_rotation(extract_number_or_distribution,local,prefix)


def extract_number_or_distribution(resources,key, variable_name):
    resource = resources.get_resource(key)
    if isinstance(resource,DistributionResource):
        return resource.create_distribution(variable_name)
    else:
        return resource.unwrap()


def extract_estimation(resources,key, *args):
    resource = resources.get_resource(key)
    if isinstance(resource, DistributionResource):
        return resource.get_estimation()
    else:
        return resource.unwrap()


def equatorial_fields(template):
    return ResourceRequest({
        "declination": dict(display_name="Declination [°]", default_value=template()),
        "hour_angle": dict(display_name="Hour angle [°]", default_value=template()),
        "own_rotation": dict(display_name="Own rotation [°]", default_value=template()),
    })


def local_fields(template):
    return ResourceRequest({
        "alt": dict(display_name="Altitude [°]", default_value=template()),
        "az": dict(display_name="Azimuth [°]", default_value=template()),
        "own_rotation": dict(display_name="Own rotation [°]", default_value=template()),
    })


class EquatorialBaseOrientation(CombineResource,Orientation):
    def get_rotation(self, extractor,local:Quaternion,prefix="orientation"):
        dec = extractor(self.data,"declination",prefix+"_dec")*np.pi/180
        ha = extractor(self.data, "hour_angle", prefix+"_ha")*np.pi/180
        rot = extractor(self.data,"own_rotation", prefix+"_own_rot")*np.pi/180
        if None in [ha,dec,rot]:
            return None
        return equatorial(dec,ha,rot)


class LocalBaseOrientation(CombineResource,Orientation):
    def get_rotation(self, extractor,local:Quaternion,prefix):
        alt = extractor(self.data, "alt", prefix+"_alt") * np.pi / 180
        az = extractor(self.data, "az", prefix+"_az") * np.pi / 180
        rot = extractor(self.data, "own_rotation", prefix + "_own_rot") * np.pi / 180
        prerot = Quaternion.rotate_xz(np.pi)*Quaternion.rotate_zy(np.pi/2)
        if None in [alt,az,rot]:
            return None
        return local*local_data(alt,az,rot)*prerot


class EquatorialPriorResource(EquatorialBaseOrientation):
    Fields = equatorial_fields(lambda: template_normal(0.0, 1.0))
    pass


class EquatorialPointResource(EquatorialBaseOrientation):
    Fields = equatorial_fields(lambda: 0.0)
    pass


class LocalPriorResource(LocalBaseOrientation):
    Fields = local_fields(lambda: template_normal(0.0, 1.0))
    pass


class LocalPointResource(LocalBaseOrientation):
    Fields = local_fields(lambda: 0.0)
    pass


class OrientationPriorResource(AlternatingResource):
    Variants = [
        ResourceVariant(EquatorialPriorResource,"Equatorial"),
        ResourceVariant(LocalPriorResource,"Local"),
    ]

    def get_rotation_estimation(self,local,prefix):
        return self.value.get_rotation_estimation(local,prefix)

    def get_prior(self,local:Quaternion,prefix):
        return self.value.get_prior(local,prefix)



class OrientationPointResource(AlternatingResource):
    Variants = [
        ResourceVariant(EquatorialPointResource,"Equatorial"),
        ResourceVariant(LocalPointResource,"Local"),
    ]

    def get_rotation_estimation(self,local,prefix):
        return self.value.get_rotation_estimation(local,prefix)

    def get_prior(self,local:Quaternion,prefix):
        return self.value.get_prior(local,prefix)

