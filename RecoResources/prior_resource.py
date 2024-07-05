import numpy as np
import pymc as pm
import pytensor.tensor as pt
from RecoResources import CombineResource, AlternatingResource, BlankResource, ResourceRequest, StrictFunction, OptionResource
from RecoResources import FloatResource, ResourceVariant, ResourceStorage
# from scipy.special import erfinv

class DistributionMaker(object):
    def create_distribution(self, name:str):
        raise NotImplementedError

    def get_dist(self):
        raise NotImplementedError

    def get_estimation(self):
        return None


class FlatMaker(BlankResource, DistributionMaker):
    Label = "Flat"

    def create_distribution(self,name:str):
        return pm.Flat(name)

    def get_dist(self):
        return pm.Flat.dist()



class HalfFlatMaker(BlankResource, DistributionMaker):
    Label = "HalfFlat"

    def create_distribution(self,name:str):
        return pm.HalfFlat(name)

    def get_dist(self):
        return pm.HalfFlat.dist()


class NormalMaker(CombineResource, DistributionMaker):
    Fields = ResourceRequest({
        "mu":dict(display_name="Mean", default_value=0.0),
        "sigma":dict(display_name="Std", default_value=1.0),
    })

    def create_distribution(self, name:str):
        return pm.Normal(name,
                         mu=self.data.get("mu"),
                         sigma=self.data.get("sigma")
                         )

    def get_dist(self):
        return pm.Normal.dist(mu=self.data.get("mu"),
                         sigma=self.data.get("sigma")
                         )

    def get_estimation(self):
        return self.data.get("mu")


class LaplaceMaker(CombineResource, DistributionMaker):
    Fields = ResourceRequest({
        "mu":dict(display_name="Mean", default_value=0.0),
        "b":dict(display_name="Scale", default_value=1.0),
    })

    def create_distribution(self, name:str):
        return pm.Laplace(name,
                         mu=self.data.get("mu"),
                         b=self.data.get("b")
                         )

    def get_dist(self):
        return pm.Laplace.dist(mu=self.data.get("mu"),
                               b=self.data.get("b")
                              )

    def get_estimation(self):
        return self.data.get("mu")


class UniformMaker(CombineResource, DistributionMaker):
    Fields = ResourceRequest({
        "lower": dict(display_name="Lower", default_value=0.0),
        "upper": dict(display_name="Upper", default_value=1.0),
    })

    def create_distribution(self, name:str):
        lower = self.data.get("lower")
        upper = self.data.get("upper")
        if lower>upper:
            lower, upper = upper, lower
        return pm.Uniform(name,lower=lower,upper=upper)

    def get_dist(self):
        lower = self.data.get("lower")
        upper = self.data.get("upper")
        if lower>upper:
            lower, upper = upper, lower
        return pm.Uniform.dist(lower=lower,upper=upper)

    def get_estimation(self):
        return (self.data.get("lower")+self.data.get("upper"))/2


class HalfNormalMaker(CombineResource, DistributionMaker):
    Fields = ResourceRequest({
        "sigma":dict(display_name="Std", default_value=1.0),
        "negate":dict(display_name="Negate",default_value=False)
    })

    def create_distribution(self, name:str):
        if self.data.get("negate"):
            neg = pm.HalfNormal(name+"_neg_", sigma=self.data.get("sigma"))
            return pm.Deterministic(name,neg)
        else:
            return pm.HalfNormal(name,sigma=self.data.get("sigma"))

    def get_dist(self):
        d = pm.HalfNormal.dist(sigma=self.data.get("sigma"))
        if self.data.get("negate"):
            return -d
        else:
            return d

    def get_estimation(self):
        #Using mean
        sigma = self.data.get("sigma")
        res = sigma*(2/np.pi)**0.5
        if self.data.get("negate"):
            return -res
        else:
            return res


class ExponentialMaker(CombineResource, DistributionMaker):
    Fields = ResourceRequest({
        "lam":dict(display_name="Lambda", default_value=1.0),
        "negate":dict(display_name="Negate",default_value=False)
    })

    def create_distribution(self, name:str):
        if self.data.get("negate"):
            neg = pm.Exponential(name+"_neg_", lam=self.data.get("lam"))
            return pm.Deterministic(name,neg)
        else:
            return pm.Exponential(name,lam=self.data.get("lam"))

    def get_dist(self):
        d = pm.Exponential.dist(lam=self.data.get("lam"))
        if self.data.get("negate"):
            return -d
        else:
            return d

    def get_estimation(self):
        lam = self.data.get("lam")
        res = 1/lam # Mean of exponential distribution
        if self.data.get("negate"):
            return -res
        else:
            return res


class ConstantMaker(CombineResource, DistributionMaker):
    Fields = ResourceRequest({
        "value":dict(display_name="Value", default_value=0.0)
    })

    def create_distribution(self, name: str):
        const = pt.constant(self.data.get("value"))
        return pm.Deterministic(name, const)

    def get_dist(self):
        const = pt.constant(self.data.get("value"))
        return const

    def get_estimation(self):
        return self.data.get("value")


class CauchyMaker(CombineResource, DistributionMaker):
    Fields = ResourceRequest({
        "alpha": dict(display_name="Location", default_value=0.0),
        "beta": dict(display_name="Scale", default_value=1.0),
    })

    def create_distribution(self, name:str):
        return pm.Cauchy(name,
                         alpha=self.data.get("alpha"),
                         beta=self.data.get("beta")
                         )

    def get_dist(self):
        return pm.Cauchy.dist(
                         alpha=self.data.get("alpha"),
                         beta=self.data.get("beta")
                         )

    def get_estimation(self):
        return self.data.get("alpha")


class DistributionResource(AlternatingResource):
    Variants = [
        ResourceVariant(ConstantMaker,"Constant"),
        ResourceVariant(NormalMaker,"Normal"),
        ResourceVariant(LaplaceMaker, "Laplace"),

        ResourceVariant(UniformMaker, "Uniform"),
        ResourceVariant(CauchyMaker, "Cauchy"),
        ResourceVariant(ExponentialMaker, "Exponential"),

        ResourceVariant(HalfNormalMaker, "Half-normal"),
        ResourceVariant(FlatMaker, "Flat"),
        ResourceVariant(HalfFlatMaker, "Half-flat"),

    ]

    def create_distribution(self, name:str):
        return self.value.create_distribution(name)

    def get_estimation(self):
        return self.value.get_estimation()


class LimitOption(OptionResource):
    OptionType = FloatResource


class TruncatedMaker(CombineResource, DistributionMaker):
    Fields = ResourceRequest({
        "lower": dict(display_name="lower", default_value=LimitOption(None)),
        "upper": dict(display_name="upper", default_value=LimitOption(None)),
        "dist": dict(display_name="upper", type_=DistributionResource)
    })

    def create_distribution(self, name: str):
        dr = self.data.get("dist")
        if isinstance(dr, ConstantMaker):
            return dr.create_distribution(name)
        dist = dr.get_dist()
        return pm.Truncated(name,
                            lower=self.data.get("lower"),
                            upper=self.data.get("upper"),
                            dist=dist,
                            )

    def get_dist(self):
        dr = self.data.get("dist")
        if isinstance(dr, ConstantMaker):
            return dr.get_dist()
        dist = dr.get_dist()
        return pm.Truncated.dist(lower=self.data.get("lower"),
                                 upper=self.data.get("upper"),
                                 dist=dist,
                                 )

    # def get_estimation(self):
    #


DistributionResource.Variants.append(ResourceVariant(TruncatedMaker, "Truncated"))


def template_uniform(a,b):
    data = ResourceStorage()
    data.set("lower",a)
    data.set("upper",b)
    return DistributionResource(UniformMaker(data))


def template_halfnormal(sigma,negate):
    data = ResourceStorage()
    data.set("sigma",sigma)
    data.set("negate",negate)
    return DistributionResource(HalfNormalMaker(data))


def template_normal(mu,sigma):
    data = ResourceStorage()
    data.set("sigma",sigma)
    data.set("mu",mu)
    return DistributionResource(NormalMaker(data))


def template_exponent(lam,negate):
    data = ResourceStorage()
    data.set("lam",lam)
    data.set("negate",negate)
    return DistributionResource(ExponentialMaker(data))

