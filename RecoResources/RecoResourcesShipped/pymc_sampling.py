import pymc as pm

from RecoResources import CombineResource, ChoiceResource, ResourceRequest, AlternatingResource, ResourceVariant


class NUTSSamplerResource(ChoiceResource):
    Choices = {
        "pymc":"PyMC (default)",
        "nutpie":"Nutpie (nuts-rs wrapper)",
        "blackjax":"BlackJAX (XLA/JAX based)",
        "numpyro":"NumPyro (pytorch based)"
    }

class PyMCSampleArgsResource(CombineResource):
    Fields = ResourceRequest({
        "draws": dict(display_name="Draws", default_value=2000),
        "tune": dict(display_name="Tune", default_value=2000),
        "chains": dict(display_name="Chains", default_value=4),
        "target_accept": dict(display_name="Target accept rate", default_value=0.95),
        "random_seed": dict(display_name="Random seed", default_value=5),
        "nuts_sampler": dict(display_name="NUTS sampler", default_value="pymc", type_=NUTSSamplerResource),
    })

    def sample(self):
        return pm.sample(
            draws=self.data.get("draws"),
            tune=self.data.get("tune"),
            chains=self.data.get("chains"),
            target_accept=self.data.get("target_accept"),
            random_seed=self.data.get("random_seed"),
            nuts_sampler=self.data.get("nuts_sampler")
        )

class AdviMethodChoiceResource(ChoiceResource):
    Choices = {
        "advi": "ADVI",
        "fullrank_advi": "Full rank ADVI",
        "svgd": "SVGD",
        "asvgd": "ASVGD"
    }

class AdviFitArgsResource(CombineResource):
    Fields = ResourceRequest({
        "random_seed": dict(display_name="Random seed", default_value=5),
        "method":dict(display_name="Method", type_=AdviMethodChoiceResource),
        "n":dict(display_name="Iterations", default_value=10000)
    })
    def get_kwargs(self):
        r = dict()
        for k in [self.Fields.requests.keys()]:
            r[k] = self.data.get(k)
        return r

class AdviDrawsArgsResource(CombineResource):
    Fields = ResourceRequest({
        "random_seed": dict(display_name="Random seed", default_value=5),
        "draws": dict(display_name="Draws", default_value=2000),
    })

    def get_kwargs(self):
        r = dict()
        for k in [self.Fields.requests.keys()]:
            r[k] = self.data.get(k)
        return r


class AdviSampleArgsResource(CombineResource):
    Fields = ResourceRequest({
        "fit_args": dict(display_name="Fit arguments", type_=AdviFitArgsResource),
        "sample_args": dict(display_name="Sample arguments", type_=AdviDrawsArgsResource),
    })

    def sample(self):
        fit_kwargs = self.data.get_resource("fit_args").get_kwargs()
        sample_kwargs = self.data.get_resource("sample_args").get_kwargs()
        approx = pm.fit(**fit_kwargs)
        return approx.sample(**sample_kwargs)


class PymcSampleAlternateResource(AlternatingResource):
    Variants = [
        ResourceVariant(PyMCSampleArgsResource,"MCMC"),
        ResourceVariant(AdviSampleArgsResource,"ADVI"),
    ]

    def sample(self):
        return self.value.sample()
