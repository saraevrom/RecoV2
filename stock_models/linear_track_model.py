import json

import numpy as np
import pymc as pm
import pytensor.tensor as pt
from matplotlib import pyplot as plt

from RecoResources import ResourceStorage, StrictFunction, Resource, DisplayList
from reco_prelude import ResourceRequest, ReconsructionModel, HDF5Resource, DetectorResource, AlternatingResource
from reco_prelude import ResourceVariant, BlankResource, CombineResource, DistributionResource, template_uniform
from reco_prelude import Scene
from RecoResources.prior_resource import template_exponent
from track_resources import PyMCSampleArgsResource, PositionPriorAlternate
from lc_resources import MainLC


def estimate(trace,key):
    return np.median(trace.posterior[key])

def d_erf(a,b,mu,sigma):
    scale = sigma*2**0.5
    return (pm.math.erf((b-mu)/scale)-pm.math.erf((a-mu)/scale))/2.0

class ImageScene(Scene):
    SceneName = "Image"

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        detector = resources.try_get("detector")
        data = resources.try_get("reco_data")
        if data is None or detector is None:
            return
        trace = resources.try_get("trace")

        frame = np.max(data, axis=0)
        lx, mx, ly, my = detector.draw(axes, frame)
        print(detector)
        axes.set_xlim(lx, mx)
        axes.set_ylim(ly, my)
        axes.set_aspect("equal")
        if trace is not None:
            x0 = estimate(trace, "X0")
            y0 = estimate(trace, "Y0")
            u0 = estimate(trace, "u0")
            phi0 = estimate(trace, "phi0") * np.pi / 180
            ts = np.array([resources.get("k_start"), resources.get("k_end")])
            k0 = resources.get("k0")
            x = x0 + u0 * np.cos(phi0) * (ts - k0)
            y = y0 + u0 * np.sin(phi0) * (ts - k0)
            axes.arrow(x[0], y[0], x[1] - x[0], y[1] - y[0], color="red", width=estimate(trace, "sigma_psf"),
                       length_includes_head=True)
        tim = resources.try_get("reco_time")
        if tim is None:
            return
        latitude = resources.get("latitude")*np.pi/180
        longitude = resources.get("longitude")*np.pi/180
        hour_angle = resources.get("hour_angle")*np.pi/180
        declination = resources.get("declination")*np.pi/180
        #own_rotation = resources.get()


    @classmethod
    def on_scene_mouse_event(cls, resources: ResourceStorage, event):
        # LMB
        if event.button == 1:
            value = True
        # RMB
        elif event.button == 3:
            value = False
        else:
            return False
        x = event.xdata
        y = event.ydata
        detector = resources.try_get("detector")
        if detector is None:
            return False
        i = detector.index_at([x, y])
        if i is None:
            return False
        return detector.set_pixel_active(i, value)


class PlotsScene(Scene):
    SceneName = "Plots"

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        detector = resources.try_get("detector")
        data = resources.try_get("reco_data")
        if data is None or detector is None:
            return
        trace = resources.try_get("trace")
        xs = np.arange(data.shape[0])
        axes.autoscale()
        axes.set_aspect("auto")
        detector = resources.try_get("detector")
        lc = np.zeros(data.shape[0])
        if detector is None:
            return
        for i in detector.iterate():
            if detector.pixel_is_active(i):
                s = (slice(None),) + i
                axes.plot(xs, data[s])
                lc += data[s]
        axes.plot(xs, lc, color="black")
        if trace is not None and resources.has_resource("lc_conf"):
            lc_params = resources.get("lc_conf")
            lc_conf: MainLC = Resource.unpack(json.loads(lc_params))
            x_lc = np.arange(resources.get("k_start"), resources.get("k_end"), 0.1)
            y_lc = lc_conf.get_lc(trace, x_lc - resources.get("k0"))
            axes.plot(x_lc, y_lc, "--", color="red")

    @classmethod
    def on_scene_mouse_event(cls, resources: ResourceStorage, event):
        return False


class PlotsAltScene(Scene):
    SceneName = "Plots (Alt)"

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        detector = resources.try_get("detector")
        data = resources.try_get("reco_data")
        if data is None or detector is None:
            return
        trace = resources.try_get("trace")
        xs = np.arange(data.shape[0])
        axes.autoscale()
        axes.set_aspect("auto")
        detector = resources.try_get("detector")
        lc = np.zeros(data.shape[0])
        if detector is None:
            return
        accum = []
        metrics = []
        w = resources.get("ma_filter")
        active_win = resources.get("active_window")
        for i in detector.iterate():
            if detector.pixel_is_active(i):
                s = (slice(None),) + i
                #axes.plot(xs, data[s])
                ydata = np.convolve(data[s], np.ones(w), 'same') / w
                accum.append(ydata)
                maxpos = np.argmax(ydata)
                metrics.append(maxpos)
                ydata[:max(0,maxpos-active_win)] = 0.0
                ydata[min(len(ydata),maxpos+active_win):] = 0.0
                lc += ydata
        accum = np.array(accum)
        order = np.argsort(metrics)
        axes.stackplot(xs,accum[order])
        #axes.plot(xs, lc, color="black")


        if trace is not None and resources.has_resource("lc_conf"):
            lc_params = resources.get("lc_conf")
            lc_conf: MainLC = Resource.unpack(json.loads(lc_params))
            x_lc = np.arange(resources.get("k_start"), resources.get("k_end"), 0.1)
            y_lc = lc_conf.get_lc(trace, x_lc - resources.get("k0"))
            axes.plot(x_lc, y_lc, "--", color="red")


    @classmethod
    def on_scene_mouse_event(cls, resources: ResourceStorage, event):
        return False



class LinearTrackModel(ReconsructionModel):
    RequestedResources = ResourceRequest({
        "k_start": dict(display_name="Start frame",default_value=0),
        "k_end": dict(display_name="End frame", default_value=-1),
        "k0": dict(display_name="Zero frame", default_value=0.0),
        "ma_filter": dict(display_name="MA filter", default_value=1, category="Display"),
        "active_window": dict(display_name="Active signal window", default_value=10, category="Display"),
        "pymc_sampling": dict(display_name="PyMC arguments", type_=PyMCSampleArgsResource),
        "detector": dict(display_name="Detector", type_=DetectorResource),
        "reco_data": dict(display_name="Reconstruction data", type_=HDF5Resource),
        "reco_time": dict(display_name="Reconstruction time", type_=HDF5Resource),
        "ref_position": dict(display_name="(X0,Y0) [mm]", type_=PositionPriorAlternate),
        "u0": dict(display_name="U0 [mm/fr]", default_value=template_uniform(0.01,2.0)),
        "phi0": dict(display_name="Phi0 [deg]", default_value=template_uniform(0.0,360.0)),
        "sigma_psf": dict(display_name="Sigma PSF [mm]", default_value=template_exponent(0.5,False)),
        "sigma": dict(display_name="Sigma 0", default_value=template_exponent(1.0,False)),
        "lc":dict(display_name="Light curve", type_=MainLC),

        "latitude": dict(display_name="Latitude [°]", default_value=0.0, category="Display"),
        "longitude": dict(display_name="Longitude [°]", default_value=0.0, category="Display"),
        "hour_angle": dict(display_name="Hour angle [°]", default_value=0.0, category="Display"),
        "declination": dict(display_name="Declination [°]", default_value=0.0, category="Display"),
        "own_rotation": dict(display_name="Own rotation [°]", default_value=0.0, category="Display"),

    })

    DisplayList = DisplayList.whitelist(["trace"])
    Scenes = [ImageScene,PlotsScene, PlotsAltScene]

    @classmethod
    def calculate(cls, resources:ResourceStorage):
        data = resources.try_get("reco_data")
        if data is None:
            return
        detector = resources.try_get("detector")
        if detector is None:
            return
        k_start = resources.get("k_start")
        k_end = resources.get("k_end")
        k0 = resources.get("k0")
        with pm.Model() as model:
            print("X0Y0",resources.get_resource("ref_position").value)
            x0,y0 = resources.get_resource("ref_position").value.get_detector_prior("X0","Y0",detector)
            u0 = resources.get_resource("u0").create_distribution("u0")
            phi0 = resources.get_resource("phi0").create_distribution("phi0")*np.pi/180.0
            sigma_psf = resources.get_resource("sigma_psf").create_distribution("sigma_psf")
            sigma = resources.get_resource("sigma").create_distribution("sigma")
            ts = np.arange(k_start,k_end)
            tensors = []
            observed = []
            x = x0 + u0*pm.math.cos(phi0)*(ts-k0)
            y = y0 + u0*pm.math.sin(phi0)*(ts-k0)
            lc = resources.get_resource("lc").make_lc(ts-k0)

            # Make columns
            #x = x[:,None]
            #y = y[:, None]
            #lc = lc[:,None]

            # def func(xp,yp):
            #     xpart = pm.math.exp(-(x-xp.T)**2/(2*sigma_psf**2))
            #     ypart = pm.math.exp(-(y-yp.T)**2/(2*sigma_psf**2))
            #     return xpart*ypart*lc/(2*np.pi*sigma_psf**2)

            for pixel in detector.pixels:
                i = pixel.index
                if detector.pixel_is_active(i):
                    s = (slice(k_start, k_end),) + i
                    min_x, max_x, min_y, max_y = pixel.get_bounds()
                    v = lc*d_erf(min_x,max_x,x,sigma_psf)*d_erf(min_y,max_y,y,sigma_psf)
                    # v = pixel.integrate(func,backend=pm.math)
                    tensors.append(v)
                    observed.append(data[s])
            tensors = pt.concatenate(tensors)
            observed = np.concatenate(observed)
            pm.Normal("likelyhood",mu=tensors,sigma=sigma,observed=observed)
            trace = resources.get_resource("pymc_sampling").sample()
            resources.set("trace",trace)
            lc_conf = resources.get_resource("lc").pack()
            resources.set("lc_conf",json.dumps(lc_conf))