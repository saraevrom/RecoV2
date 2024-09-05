from matplotlib import pyplot as plt
import numpy as np
from scipy.optimize import curve_fit, minimize

from reco_prelude import ResourceStorage, ReconsructionModel, ResourceRequest, LabelledAction
from reco_prelude import HDF5Resource, DetectorResource, Scene




class DetectorScene(Scene):
    SceneName = "Detector"

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        detector = resources.try_get("detector")
        data = resources.try_get("reco_data")
        if data is None or detector is None:
            return
        #trace = resources.try_get("trace")

        frame = np.max(data, axis=0)
        lx, mx, ly, my = detector.draw(axes, frame)
        axes.set_xlim(lx, mx)
        axes.set_ylim(ly, my)
        axes.set_aspect("equal")

        trajectory:np.ndarray = resources.try_get("trajectory")
        if trajectory is not None:
            xs = trajectory[:,1]
            ys = trajectory[:,2]
            axes.plot(xs,ys,"-x", color="red")

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
        #axes.plot(xs, lc, color="black")

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

class BarycentricTrackModel(ReconsructionModel):
    '''
    A fairly simple track reconstruction method.
    '''
    RequestedResources = ResourceRequest({
        "reco_data": dict(display_name="Reconstruction data", type_=HDF5Resource),
        "detector": dict(display_name="Detector", type_=DetectorResource),
        "signal_threshold": dict(display_name="Signal threshold", default_value=3.0),
        "duration_threshold":dict(display_name="Duration threshold", default_value=0.0),
        "use_robust_linreg":dict(display_name="Robust linear regression", default_value=False),
        "use_real_signal":dict(display_name="Use real signal for barycenter estimation", default_value=False),
    })

    Scenes = [DetectorScene, PlotsScene, PlotX,PlotY]

    AdditionalLabels = {
        "trajectory": "Trajectory",
    }

    @classmethod
    def calculate(cls, resources: ResourceStorage):
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
            u = (kx**2+ky**2)**0.5
            phi = np.arctan2(ky,kx)*180/np.pi
            resources.set("u0",u)
            resources.set("phi",phi)
        else:
            opt_del("u0")
            opt_del("phi")


    @LabelledAction("Select pixels")
    @staticmethod
    def select_pixels(resources):
        print("Select action start")
        #print(resources)
        reco_data = resources.get("reco_data")
        detector = resources.get("detector")
        sigma_thresh = resources.get("signal_threshold")
        for i in detector.iterate():
            s = (slice(None),) + i
            ydata = reco_data[s]
            xdata = np.arange(len(ydata))
            ok = True
            try:
                popt,perr = fit_pixel(xdata, ydata)
                b0, b1, b2, a, x0, sd = popt
                sb0, sb1, sb2, sa, sx0, ssd = perr
                if a<=3*sa:
                    #Condition 2 fail:  the fitted value of the Gaussian height is not big enough
                    ok = False

                sigma = (np.mean((ydata-track_approx(xdata,b0, b1, b2, a, x0, sd))**2))**0.5
                y_flat = track_approx(xdata,b0, b1, b2, 0.0, x0, sd)
                if not ((ydata-y_flat)>sigma_thresh*sigma).any():
                    # Condition 3 fail: lightcurve does not have any points larger than 3 sigma
                    ok = False

                if x0<0 or x0>xdata[-1]:
                    # Condition 4 fail: x0 if out of bounds
                    ok = False

                if sd<resources.get("duration_threshold"):
                    # Condition 5 fail...ish : peak is not long enough
                    ok = False

                print(popt, sigma)
            except RuntimeError:
                # Condition 1 fail: not a successful convergence
                print("No convergence")
                ok = False
            detector.set_pixel_active(i,ok)