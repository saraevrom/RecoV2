import numpy as np
import pymc as pm
import pytensor.tensor as pt

from RecoResources import AlternatingResource, DistributionResource, CombineResource, BlankResource
# from RecoResources.RecoResourcesShipped.prior_resource import template_exponent, template_uniform
from RecoResources import ResourceRequest, ResourceVariant

from RecoResources.RecoResourcesShipped.prior_resource import template_exponent, template_uniform


# BlankResource = Resource.lookup_resource("BlankResource")
# CombineResource = Resource.lookup_resource("CombineResource")
# DistributionResource = Resource.lookup_resource("DistributionResource")
# AlternatingResource = Resource.lookup_resource("AlternatingResource")

def estimate(trace,key):
    return np.median(trace.posterior[key])


class LCMaker(object):
    def make_lc(self, var_name,x):
        raise NotImplementedError

    def get_lc(self,trace,var_name,x):
        raise NotImplementedError


class ConstantLC(BlankResource,LCMaker):
    Label = "Constant light curve"

    def make_lc(self, var_name,x):
        if hasattr(x,"shape"):
            return pt.ones(x.shape)
        else:
            return 1.0

    def get_lc(self,trace,var_name,x):
        return np.ones(x.shape)


class LinearLC(CombineResource,LCMaker):
    Fields = ResourceRequest({
        "tau":dict(display_name="Tau", type_=DistributionResource, default_value=template_exponent(1.0,False)),
    })

    def make_lc(self, var_name,x):
        tau = self.data.get_resource("tau")
        d = tau.create_distribution(var_name+"_tau")
        r = 1+x/d
        return pt.switch(r>0.0,r,0.0)

    def get_lc(self,trace,var_name,x):
        tau = estimate(trace,var_name+"_tau")
        r = 1+x/tau
        return np.where(r>0.0,r,0.0)


class ExponentLC(CombineResource,LCMaker):
    Fields = ResourceRequest({
        "tau": dict(display_name="Tau", type_=DistributionResource, default_value=template_exponent(1.0,False)),
    })

    def make_lc(self, var_name,x):
        tau = self.data.get_resource("tau")
        d = tau.create_distribution(var_name+"_tau")
        return pt.exp(x/d)

    def get_lc(self,trace,var_name,x):
        tau = estimate(trace,var_name+"_tau")
        return np.exp(x/tau)


class GaussianLC(CombineResource,LCMaker):
    Fields = ResourceRequest({
        "tau": dict(display_name="Tau", type_=DistributionResource, default_value=template_exponent(1.0,False)),
        "offset": dict(display_name="Offset", type_=DistributionResource)
    })

    def make_lc(self, var_name,x):
        tau = self.data.get_resource("tau")
        tau = tau.create_distribution(var_name+"_tau")
        off = self.data.get_resource("offset")
        off = off.create_distribution(var_name+"_off")
        return pm.math.exp(-((x-off)**2/(2*tau**2)))

    def get_lc(self,trace,var_name,x):
        tau = estimate(trace, var_name + "_tau")
        off = estimate(trace, var_name + "_off")
        return np.exp(-((x - off) ** 2 / (2 * tau ** 2)))


class LCAlter(AlternatingResource,LCMaker):
    Variants = [
        ResourceVariant(ConstantLC,"Constant"),
        ResourceVariant(LinearLC,"Linear"),
        ResourceVariant(ExponentLC,"Exponential"),
        ResourceVariant(GaussianLC,"Gaussian")
    ]

    def make_lc(self, var_name, x):
        return self.value.make_lc(var_name,x)

    def get_lc(self,trace,var_name,x):
        return self.value.get_lc(trace,var_name,x)


class DualLC(CombineResource,LCMaker):
    Fields = ResourceRequest({
        "left":dict(display_name="Left",type_=LCAlter),
        "right":dict(display_name="Right",type_=LCAlter),
        "negate_right":dict(display_name="Negate right", default_value=True),
        "offset":dict(display_name="Offset", type_=DistributionResource)
    })

    def make_lc(self, var_name,x):
        offset = self.data.get_resource("offset").create_distribution(var_name+"_offset")
        x = x-offset
        left = self.data.get_resource("left").make_lc(var_name+"_left",x)
        if self.data.get("negate_right"):
            right = self.data.get_resource("right").make_lc(var_name+"_right",-x)
        else:
            right = self.data.get_resource("right").make_lc(var_name + "_right", x)
        return pm.math.switch(x<0.0,left,right)

    def get_lc(self,trace,var_name,x):
        offset = estimate(trace, var_name+"_offset")
        x = x-offset
        left = self.data.get_resource("left").get_lc(trace,var_name+"_left",x)
        if self.data.get("negate_right"):
            right = self.data.get_resource("right").get_lc(trace,var_name + "_right", -x)
        else:
            right = self.data.get_resource("right").get_lc(trace, var_name + "_right", x)
        return np.where(x<0.0, left, right)


LCAlter.Variants.append(ResourceVariant(DualLC,"Dual"))


class MainLC(CombineResource):
    Fields = ResourceRequest({
        "lc":dict(display_name="LC profile", type_=LCAlter),
        "e0":dict(display_name="E0", type_=DistributionResource, default_value=template_uniform(10.0,60.0)),
    })

    def make_lc(self,x):
        profile = self.data.get_resource("lc").make_lc("lc",x)
        e0 = self.data.get_resource("e0").create_distribution("e0")
        return e0*profile

    def get_lc(self,trace,x):
        profile = self.data.get_resource("lc").get_lc(trace, "lc", x)
        e0 = estimate(trace,"e0")
        return e0*profile
