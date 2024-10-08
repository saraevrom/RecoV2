from RecoResources import CombineResource, ResourceRequest, StrictFunction, BlankResource, ResourceVariant, \
    AlternatingResource, DistributionResource, ChoiceResource
import pymc as pm
from pymc_sampling import PyMCSampleArgsResource
import numpy as np
from transform import TransformBuilder, ecef_align, projection_matrix




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

    def get_detector_prior(self,x_name,y_name,detector):
        # minx,maxx,miny,maxy = detector.get_active_bounds()
        x_prior = self.data.get_resource("x_prior").create_distribution(x_name)
        y_prior = self.data.get_resource("y_prior").create_distribution(y_name)
        return x_prior, y_prior


class PositionPriorAlternate(AlternatingResource):
    Variants = [
        ResourceVariant(AutoPositionPrior, "Automatic"),
        ResourceVariant(ManualPositionPrior, "Manual")
    ]
