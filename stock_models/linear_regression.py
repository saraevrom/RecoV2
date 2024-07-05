import numpy as np
import pymc as pm
from matplotlib import pyplot as plt

from RecoResources import ResourceStorage
from reco_prelude import ResourceRequest, ReconsructionModel, HDF5Resource


class LinearRegression(ReconsructionModel):
    RequestedResources = ResourceRequest({
        "x": dict(display_name="X", type_=HDF5Resource),
        "y": dict(display_name="Y", type_=HDF5Resource),
    })
    Scenes = ["L","S","LS"]

    @classmethod
    def calculate(cls, resources:ResourceStorage):
        x = resources.get("x")
        y = resources.get("y")
        with pm.Model() as model:
            k = pm.HalfFlat("k")
            b = pm.Flat("b")
            s = pm.HalfNormal("s",10)
            o = pm.Normal("o", mu=x*k+b, sigma=s, observed=y)
            trace = pm.sample(tune=1000, draws=2000, chains=4)
        resources.set("trace", trace)

    @classmethod
    def draw_scene(cls, resources:ResourceStorage, fig: plt.Figure, axes: plt.Axes, scene):
        if scene is None:
            return
        if "S" in scene:
            x = resources.try_get("x")
            y = resources.try_get("y")
            if not(x is None or y is None):
                axes.scatter(x, y)

        if "L" in scene:
            trace = resources.try_get("trace")

            x = resources.try_get("x")
            if x is None:
                return
            if trace is None:
                return
            k = np.median(trace.posterior["k"])
            b = np.median(trace.posterior["b"])
            x1 = np.array([x[0],x[-1]])
            axes.plot(x1, x1*k+b)
