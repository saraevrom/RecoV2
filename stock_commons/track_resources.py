from RecoResources import CombineResource, ResourceRequest, StrictFunction, BlankResource, ResourceVariant, \
    AlternatingResource, DistributionResource
import pymc as pm
import numpy as np
from transform import TransformBuilder, ecef_align, projection_matrix


# class OrientationResource(CombineResource):
#     Fields = ResourceRequest({
#         "hour_angle": dict(display_name="Hour angle [°]", default_value=0.0),
#         "declination": dict(display_name="Declination [°]", default_value=0.0),
#         "own_rotation": dict(display_name="Own rotation [°]", default_value=0.0),
#         "focal_distance": dict(display_name="Focal distance [mm]", default_value=150.0)
#     })
#
#     def get_prior_tuple(self):
#         hour_angle = self.data.get_resource("hour_angle").create_distribution("GHA") * np.pi / 180
#         declination = self.data.get_resource("declination").create_distribution("dec") * np.pi / 180
#         own_rotation = self.data.get_resource("own_rotation").create_distribution("Omega") * np.pi / 180
#         #f = resources.get_resource("f").create_distribution("f")
#         return hour_angle,declination,own_rotation
#
#     def get_estimation_tuple(self):
#         hour_angle = self.data.get_resource("hour_angle").get_estimation()
#         declination = self.data.get_resource("declination").get_estimation()
#         own_rotation = self.data.get_resource("own_rotation").get_estimation()
#         return hour_angle, declination, own_rotation
#
#     # def make_transform(self,tup,parent=None,backend=np):
#     #     hour_angle, declination, own_rotation = tup
#     #     return TransformBuilder() \
#     #         .with_rotation(ecef_align(declination,
#     #                                   hour_angle,
#     #                                   own_rotation, backend=backend)) \
#     #         .with_parent(parent) \
#     #         .build()
#
#
#     @property
#     def focal_distance(self):
#         return self.data.get("focal_distance")
#
#     def projection_matrix(self):
#         return projection_matrix(self.focal_distance)


class PyMCSampleArgsResource(CombineResource):
    Fields = ResourceRequest({
        "draws": dict(display_name="Draws", default_value=2000),
        "tune": dict(display_name="Tune", default_value=2000),
        "chains": dict(display_name="Chains", default_value=4),
        "target_accept": dict(display_name="Target accept rate", default_value=0.95),
        "random_seed": dict(display_name="Random seed", default_value=5),
    })

    def sample(self):
        return pm.sample(
            draws=self.data.get("draws"),
            tune=self.data.get("tune"),
            chains=self.data.get("chains"),
            target_accept=self.data.get("target_accept"),
            random_seed=self.data.get("random_seed")
        )

class PositionPrior(object):
    def get_detector_prior(self,x_name,y_name,detector):
        raise NotImplementedError


class AutoPositionPrior(PositionPrior, BlankResource):
    Label = "Chooses automatically according to chosen pixels"
    def get_detector_prior(self,x_name,y_name,detector):
        minx,maxx,miny,maxy = detector.get_active_bounds()
        x_prior = pm.Uniform(x_name, minx, maxx)
        y_prior = pm.Uniform(y_name, miny, maxy)
        return x_prior, y_prior


class ManualPositionPrior(PositionPrior,CombineResource):

    Fields = ResourceRequest({
        "x_prior": dict(display_name="X", type_=DistributionResource),
        "y_prior": dict(display_name="Y", type_=DistributionResource)
    })


class PositionPriorAlternate(AlternatingResource):
    Variants = [
        ResourceVariant(AutoPositionPrior, "Automatic"),
        ResourceVariant(ManualPositionPrior, "Manual")
    ]
