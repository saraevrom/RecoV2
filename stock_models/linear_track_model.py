import json

import numpy as np
import pymc as pm
import pytensor.tensor as pt
from matplotlib import pyplot as plt
from scipy.optimize import curve_fit, minimize

from RecoResources import ResourceStorage, Resource, DisplayList
# from reco_prelude import ResourceRequest, ReconsructionModel, HDF5Resource, AlternatingResource, LabelledAction
# from reco_prelude import ResourceVariant, BlankResource, CombineResource, DistributionResource, template_uniform
# from reco_prelude import Scene
from RecoResources import ResourceRequest
from reconstruction_model import ReconstructionModel, LabelledAction, Scene

from RecoResources.RecoResourcesShipped.prior_resource import ConstantMaker, ExponentialMaker, UniformMaker
from padamo_rs_detector_parser import FixedNorm

# INCLUDE track_resources
# INCLUDE detector_resource
# INCLUDE lc_resources
# INCLUDE measurements_resources

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
        max_ = resources.get("Signal_max")
        if max_ > 0:
	        min_ = resources.get("Signal_min")
	        lx, mx, ly, my = detector.draw(axes, frame, FixedNorm(min_, max_))
        else:
	        lx, mx, ly, my = detector.draw(axes, frame)
        print(detector)
        axes.set_xlim(lx, mx)
        axes.set_ylim(ly, my)
        axes.set_aspect("equal")
        if trace is not None:
            x0 = estimate(trace, "X0")
            y0 = estimate(trace, "Y0")
            phi0 = estimate(trace, "phi0")
            u0 = estimate(trace, "u0") / 1000.
            a0 = estimate(trace, "a0") / 1000.
            ts = np.array([resources.get("k_start"), resources.get("k_end")])
            k0 = resources.get("k0")
            x = x0 + np.cos(phi0*np.pi/180.0) * (ts - k0) * ( u0 + a0 * (ts - k0)/2. )
            y = y0 + np.sin(phi0*np.pi/180.0) * (ts - k0) * ( u0 + a0 * (ts - k0)/2. )
            axes.arrow(x[0], y[0], x[1] - x[0], y[1] - y[0], color="red", width=estimate(trace, "sigma_psf"),
                       length_includes_head=True)
#        tim = resources.try_get("reco_time")
#        if tim is None:
#            return
        latitude = resources.get("latitude")*np.pi/180
        longitude = resources.get("longitude")*np.pi/180
        hour_angle = resources.get("hour_angle")*np.pi/180
        declination = resources.get("declination")*np.pi/180
        #own_rotation = resources.get()
        
        trajectory:np.ndarray = resources.try_get("trajectory")
        if trajectory is not None:
            xs = trajectory[:,1]
            ys = trajectory[:,2]
            axes.plot(xs, ys, "-x", color="red")


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
        w = resources.get("ma_filter")
        active_win = resources.get("active_window")
        for i in detector.iterate():
            if detector.pixel_is_active(i):
                s = (slice(None),) + i
                ydata = np.convolve(data[s], np.ones(w), 'same') / w
                maxpos = np.argmax(ydata)
                ydata[:max(0,maxpos-active_win)] = 0.0
                ydata[min(len(ydata),maxpos+active_win):] = 0.0
                axes.plot(xs, ydata)
                lc += ydata
        axes.plot(xs, lc, color="black")
        if trace is not None and resources.has_resource("lc_conf"):
            lc_params = resources.get("lc_conf")
            lc_conf = Resource.unpack(json.loads(lc_params))
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
            lc_conf = Resource.unpack(json.loads(lc_params))
            x_lc = np.arange(resources.get("k_start"), resources.get("k_end"), 0.1)
            y_lc = lc_conf.get_lc(trace, x_lc - resources.get("k0"))
            axes.plot(x_lc, y_lc, "--", color="red")


    @classmethod
    def on_scene_mouse_event(cls, resources: ResourceStorage, event):
        return False



class PlotAxis(Scene):
    SceneName = "Plot Axis"
    SECOND_AXIS=0
    K_LABEL = ""
    B_LABEL = ""

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        trajectory = resources.get("trajectory")
        axes.autoscale()
        axes.set_aspect("auto")
        if trajectory is None:
            return
        axes.plot(trajectory[:,0], trajectory[:,cls.SECOND_AXIS], "o", color="black")

        if resources.has_resource(cls.K_LABEL) and resources.has_resource(cls.B_LABEL):
            axes.plot(trajectory[:,0],trajectory[:,0]*resources.get(cls.K_LABEL)+resources.get(cls.B_LABEL),
                      color="black")

    @classmethod
    def on_scene_mouse_event(cls, resources: ResourceStorage, event):
        return False


class PlotX(PlotAxis):
    SceneName = "Plot X(t)"
    SECOND_AXIS = 1
    K_LABEL = "kx"
    B_LABEL = "bx"

class PlotY(PlotAxis):
    SceneName = "Plot Y(t)"
    SECOND_AXIS = 2
    K_LABEL = "ky"
    B_LABEL = "by"

def track_approx(x,b0,b1,b2,a,x0,sd):
    return b0+b1*x+b2*x**2+a*np.exp(-0.5*((x-x0)/sd)**2)


def trunc_track_approx(x,a,x0,sd):
    return a*np.exp(-0.5*((x-x0)/sd)**2)

def fit_pixel(xdata,ydata):
    p0 = np.array([0.0, 0.0, 0.0, np.max(ydata), np.argmax(ydata), 1.0])
    popt, pcov = curve_fit(track_approx, xdata, ydata, p0, method="lm")
    perr = np.sqrt(np.diag(pcov))
    return popt,perr


class LinearTrackModel(ReconstructionModel):
    RequestedResources = ResourceRequest({
        "detector": dict(display_name="Detector", type_="DetectorResource"),
        "reco_data": dict(display_name="Reconstruction data", type_="HDF5Resource"),
        "reco_time": dict(display_name="Reconstruction time", type_="HDF5Resource"),
        "pymc_sampling": dict(display_name="PyMC arguments", type_="PyMCSampleArgsResource"),
        "k_start": dict(display_name="Start frame",default_value=0),
        "k_end": dict(display_name="End frame", default_value=-1),
        "k0": dict(display_name="Zero frame", default_value=0.0),
        "measurement_error": dict(display_name="Measurement error", type_="MeasurementErrorAlternate"),
        "sigma_psf": dict(display_name="Sigma PSF [mm]", default_value=ExponentialMaker.template(0.5,False)),

        "ref_position": dict(display_name="(X0,Y0) [mm]", type_="PositionPriorAlternate", category="Priors"),
        "pre_reco": dict(display_name="Use Pre-reco (phi0, u0)", default_value=False, category="Priors"),
        
        "phi0": dict(display_name="Phi0 [deg]", default_value=UniformMaker.template(0.0,360.0), category="Priors"),
        "u0": dict(display_name="U0 [mm/fr]*1000", default_value=UniformMaker.template(0.01,2.0), category="Priors"),
        "a0": dict(display_name="A0 [mm/fr2]*1000", default_value=ConstantMaker.template(0.0), category="Priors"),
        "lc":dict(display_name="Light Сurve", type_="MainLC", category="Priors"),

        "Signal_min": dict(display_name="Signal min", default_value=0.0, category="Display"),
        "Signal_max": dict(display_name="Signal max", default_value=-1.0, category="Display"),
        "ma_filter": dict(display_name="MA filter", default_value=1, category="Display"),
        "active_window": dict(display_name="Active signal window", default_value=150, category="Display"),
        "latitude": dict(display_name="Latitude [°]", default_value=0.0, category="Display"),
        "longitude": dict(display_name="Longitude [°]", default_value=0.0, category="Display"),
        "hour_angle": dict(display_name="Hour angle [°]", default_value=0.0, category="Display"),
        "declination": dict(display_name="Declination [°]", default_value=0.0, category="Display"),
        "own_rotation": dict(display_name="Own rotation [°]", default_value=0.0, category="Display"),
        
        "signal_threshold": dict(display_name="Signal threshold", default_value=3.0, category="Selection"),
        "duration_threshold": dict(display_name="Duration threshold", default_value=0.0, category="Selection"),
        "use_robust_linreg": dict(display_name="Robust linear regression", default_value=False, category="Selection"),
        "use_real_signal": dict(display_name="Use real signal for barycenter estimation",
                                default_value=False, category="Selection"),

    })

    DisplayList = DisplayList.whitelist(["trace"])
    Scenes = [ImageScene, PlotsScene, PlotsAltScene, PlotX, PlotY]
    
    AdditionalLabels = { "trajectory": "Trajectory", }
    
    @LabelledAction("Pre-reco (barycentric)")
    @staticmethod
    def barycentric_reco(resources):
    #def barycentric_reco(cls, resources: ResourceStorage):
        print("BARY START")
        reco_data = resources.get("reco_data")
        detector = resources.get("detector")
        print(reco_data)
        pixel_activations = dict()
        xdata = np.arange(reco_data.shape[0])
        use_real = resources.get("use_real_signal")
        for i in detector.iterate():
            if detector.pixel_is_active(i):
                s = (slice(None),) + i
                ydata = reco_data[s]
                try:
                    popt,perr = fit_pixel(xdata, ydata)
                    b0, b1, b2, a, x0, sd = popt
                    pixel_activations[i] = popt
                    print(f"Pixel {i} is active in interval {pixel_activations[i]}")
                except RuntimeError:
                    print("No convergence...")

        data = []
        for t in xdata:
            x = 0.0
            y = 0.0
            xy_sum = 0.0
            has_signal = False
            for pixel in detector.pixels:
                if detector.pixel_is_active(pixel.index):
                    if pixel.index in pixel_activations.keys():
                        popt = pixel_activations[pixel.index]
                        b0, b1, b2, a, x0, sd = popt
                        t_start = x0-3*sd
                        t_end = x0+3*sd
                        if t_start<=t<=t_end:
                            data_index = (t,) + pixel.index
                            #print("DATA INDEX", data_index)
                            #s = float(reco_data[data_index])
                            if use_real:
                                s = float(reco_data[data_index]) - (b0+b1*t+b2*t**2)
                            else:
                                s = a*np.exp(-0.5*((t-x0)/sd)**2)
                            x += s*np.mean(pixel.vertices[:, 0])
                            y += s*np.mean(pixel.vertices[:, 1])
                            xy_sum += s
                            has_signal = True
            if xy_sum != 0:
                x /= xy_sum
                y /= xy_sum
            if not has_signal:
                continue
            #print(t,x,y)
            data.append([t,x,y])
        data = np.array(data)
        resources.set("trajectory",data)
        trajectory = data
        use_robust = resources.get("use_robust_linreg")

        def linreg(x,k,b):
            return k*x+b

        def opt_del(label):
            if resources.has_resource(label):
                resources.delete_resource(label)

        if use_robust:
            used_loss = "soft_l1"
        else:
            used_loss = "linear"

        def mod_fit(axis,k_label,b_label):
            try:
                popt,pcov = curve_fit(linreg,trajectory[:,0],trajectory[:,axis],p0=np.array([1.0,0.0]),
                                      method="dogbox", loss=used_loss)
                kx, bx = popt
                #axes.plot(trajectory[:,0],linreg(trajectory[:,0],*popt), color="black")
                resources.set(k_label,kx)
                resources.set(b_label,bx)
            except RuntimeError:
                opt_del(k_label)
                opt_del(b_label)

        mod_fit(1,"kx","bx")
        mod_fit(2,"ky","by")
        kx = resources.try_get("kx")
        ky = resources.try_get("ky")
        if kx is not None and ky is not None:
            u = (kx**2+ky**2)**0.5 * 1000.
            phi = np.arctan2(ky,kx)*180/np.pi
            resources.set("u_pre",u)
            resources.set("phi_pre",phi)  
            print("PRE_RECO: Phi0, U0", phi, u)
        else:
            opt_del("u_pre")
            opt_del("phi_pre")

    

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
            
            if resources.has_resources("pre_reco", "phi_pre", "u_pre"):
                phi_min = resources.get("phi_pre") - 20.
                phi_max = resources.get("phi_pre") + 20.
                u_min = resources.get("u_pre") * 0.75
                u_max = resources.get("u_pre") * 1.5
                phi0 = pm.Uniform("phi0", phi_min, phi_max )
                u0 = pm.Uniform("u0", u_min, u_max)
                print("RECO use PRE_RECO for Phi0 and U0 priors: ")
                print("Phi0: Uniform " , phi_min, phi_max)
                print("U0: Uniform " , u_min, u_max)
            else:    
                phi0 = resources.get_resource("phi0").create_distribution("phi0")
                u0 = resources.get_resource("u0").create_distribution("u0")

            a0 = resources.get_resource("a0").create_distribution("a0")
            
            sigma_psf = resources.get_resource("sigma_psf").create_distribution("sigma_psf")
#           sigma = resources.get_resource("sigma").create_distribution("sigma")
#			nu = resources.get_resource("nu").create_distribution("nu")

            ts = np.arange(k_start,k_end)
            tensors = []
            observed = []
            x = x0 + pm.math.cos(phi0*np.pi/180.0)*(ts-k0) * ( u0 + a0 * (ts-k0)/2. ) / 1000.
            y = y0 + pm.math.sin(phi0*np.pi/180.0)*(ts-k0) * ( u0 + a0 * (ts-k0)/2. ) / 1000.
            lc = resources.get_resource("lc").make_lc(ts-k0)


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
            resources.get_resource("measurement_error").get_likelyhood(tensors, observed)
#            pm.Normal("likelyhood",mu=tensors,sigma=sigma,observed=observed)
#            pm.StudentT("likelyhood",nu=nu,mu=tensors,sigma=sigma,observed=observed)

            trace = resources.get_resource("pymc_sampling").sample()
            resources.set("trace",trace)
            lc_conf = resources.get_resource("lc").pack()
            resources.set("lc_conf",json.dumps(lc_conf))
