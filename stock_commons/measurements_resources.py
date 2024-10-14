from RecoResources import CombineResource, ResourceRequest, StrictFunction, BlankResource, ResourceVariant, \
    AlternatingResource, DistributionResource
import pymc as pm
import numpy as np
from transform import TransformBuilder, ecef_align, projection_matrix
from RecoResources.prior_resource import template_exponent


class MeasurementErrorModel(object):

    def get_likelyhood(self, mu_model, observed):
        raise NotImplementedError


class GaussianErrorModel(MeasurementErrorModel, CombineResource):
    Fields = ResourceRequest({
        "sigma": dict(display_name="Sigma", default_value=template_exponent(1.0, False))
    })

    def get_likelyhood(self, mu_model, observed):
        sigma = self.data.get_resource("sigma").create_distribution("sigma_measurement")
        return pm.Normal("likelyhood", mu=mu_model, sigma=sigma, observed=observed)


class StudentErrorModel(MeasurementErrorModel, CombineResource):
    Fields = ResourceRequest({
        "sigma": dict(display_name="Sigma", default_value=template_exponent(1.0, False)),
        "nu": dict(display_name="Nu", default_value=template_exponent(1.0, False))
    })

    def get_likelyhood(self, mu_model, observed):
        sigma = self.data.get_resource("sigma").create_distribution("sigma_measurement")
        nu = self.data.get_resource("nu").create_distribution("nu_measurement")
        return pm.StudentT("likelyhood", mu=mu_model, nu=nu, sigma=sigma, observed=observed)


class MeasurementErrorAlternate(AlternatingResource):
    Variants = [
        ResourceVariant(GaussianErrorModel, "Gaussian"),
        ResourceVariant(StudentErrorModel, "Student")
    ]

    def get_likelyhood(self, mu_model, observed):
        return self.value.get_likelyhood(mu_model, observed)

