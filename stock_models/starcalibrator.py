from datetime import datetime

import numpy as np
import numba as nb
import pymc as pm
import pytensor.tensor as pt
from matplotlib import pyplot as plt

from RecoResources import ResourceStorage
from padamo_rs_detector_parser import PadamoDetector
from reco_prelude import ReconsructionModel, ResourceRequest, HDF5Resource, TimeResource, DetectorResource
from reco_prelude import template_normal, NumpyArrayResource, Scene, template_exponent, template_halfnormal
from RecoResources.prior_resource import ConstantMaker
from transform import Transform, unixtime_to_era, Quaternion, Vector3, TransformBuilder, observatory_transform
from transform import ecef_align, projection_matrix, simple_projection_matrix, Vector4
from stars import StarList
from star_pin import PinnedStars
from orientation import OrientationPriorResource
from track_resources import PyMCSampleArgsResource
from transform import Matrix
from reco_prelude import LabelledAction
from matplotlib.patches import  Circle

# WORK IN PROGRESS


def scene_3d(resources,era,orientation_getter,backend=np):
    latitude = resources.get("latitude") * np.pi / 180.0
    longitude = resources.get("longitude") * np.pi / 180.0
    earth: Transform = TransformBuilder().with_rotation(Quaternion.rotate_xy(era)).build()

    # Make observatory and attach it to Earth.
    # Neglect position
    observatory:Transform = observatory_transform(latitude, longitude, apply_position=False)
    observatory.parent = earth
    detector_orientation = orientation_getter(observatory.rotation,"orientation")
    if detector_orientation is None:
        return
    detector:Transform = TransformBuilder() \
        .with_rotation(detector_orientation) \
        .with_parent(earth)\
        .build()

    return earth, observatory, detector


def scene_3d_view(resources,dt=None):
    orientation = resources.get_resource("orientation")
    # chosen_stars = resources.get("stars")
    f = resources.get_resource("f").get_estimation()

    if dt is None:
        dt = resources.get("time_probe").timestamp()
    else:
        print("UNIXTIME override:",dt)
    era = unixtime_to_era(dt)
    return scene_3d(resources, era, orientation.get_rotation_estimation)


def get_stars():
    return StarList.fetch_filtered(["ra", "dec", "vmag", "ub", "bv"])


def transform_starvec(suitable_stars,vp):
    vec = suitable_stars.pack_stars_eci()
    model_column = vec.to_column4()
    star_scattered = vp @ model_column
    star_scattered = star_scattered.to_vec4().to_vec3()
    return star_scattered.unpack()


def get_vp(observer:Transform,f=1):
    proj = projection_matrix(f)
    view = observer.view_matrix()
    return proj @ view

def anti_altaz_represent(x,y,z):
    """
    turn cartesian direction into alt,az
    x,y,z are in OCEF
    """
    horizontal = (x**2+y**2)**0.5
    ralt = 90-np.arctan2(z,horizontal)*180/np.pi
    az = np.arctan2(x,y)
    return ralt,az

def d_erf(a,b,mu,sigma):
    scale = sigma*2**0.5
    return (pm.math.erf((b-mu)/scale)-pm.math.erf((a-mu)/scale))/2.0

def get_current_frame(resources,time_data):
    k = resources.get("frame_probe")
    if k < 0:
        k = 0
    if k >= time_data.shape[0]:
        k = time_data.shape[0] - 1
    return k


@nb.njit(nb.bool_[:,:,:](nb.bool_[:,:,:],nb.int64,nb.int64,nb.int64))
def flood_fill(data,t0,x0,y0):
    stack = nb.typed.List()
    result = np.full(fill_value=False,shape=data.shape)
    result[t0,x0,y0] = True
    stack.append((t0,x0,y0))
    cnt = 0
    while len(stack)>0:
        #print(stack)
        (t, x, y) = stack.pop()
        result[t, x, y] = True
        cnt += 1
        for t1 in [t-1,t, t+1]:
            for x1 in [x-1,x, x+1]:
                for y1 in [y-1,y, y+1]:
                    valid_bounds = 0 <= t1 < data.shape[0] and 0 <= x1 < data.shape[1] and 0 <= y1 < data.shape[2]
                    noncolliding = not (t1==t and x1==x and y1==y)
                    needs_it = data[t1,x1,y1] and not result[t1,x1,y1]
                    #print("Check", (t1, x1, y1),valid_bounds,noncolliding,needs_it)
                    if valid_bounds and noncolliding and needs_it:
                        #print("Should add", (t1, x1, y1))
                        stack.append((t1, x1, y1))
    print(f"Filled {cnt} values")
    return result

class SkyScene(Scene):
    SceneName = "Sky"

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        dat = scene_3d_view(resources)
        if dat is None:
            return
        earth, observatory, detector = dat
        suitable_stars = get_stars()
        #vp = get_vp(observatory)
        view_matrix = observatory.view_matrix()
        x,y,z = transform_starvec(suitable_stars,view_matrix)

        f = resources.get_resource("f").get_estimation()
        mags = np.array([x.vmag for x in suitable_stars])
        chosen_stars = resources.get_resource("star_list").get_stars()

        visible = z > 0
        s = 3 ** (4 - mags)

        def selection_color(x):
            if chosen_stars.contains(x):
                return "red"
            else:
                return "blue"

        print(len(suitable_stars.stars))
        c = [selection_color(v) for i, v in enumerate(suitable_stars.stars) if visible[i]]
        #axes.scatter(x[visible], y[visible], s=s[visible], c=c)
        ralt,az = anti_altaz_represent(x[visible],y[visible],z[visible])
        axes.scatter(ralt*np.sin(az),ralt*np.cos(az), s=s[visible], c=c)
        dx = resources.get_resource("plane_offset_x").get_estimation()
        dy = resources.get_resource("plane_offset_y").get_estimation()

        # Drawing FOV
        detector_data = resources.try_get("detector")
        if detector_data is not None:
            detector_data: PadamoDetector
            model = detector.model_matrix()
            neg_x = Matrix([
                [-1,0,0,0],
                [0,1,0,0],
                [0,0,1,0],
                [0,0,0,1]
            ])
            off = Matrix([
                [1, 0, 0, dx],
                [0, 1, 0, dy],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ])
            mv = view_matrix @ model @ neg_x
            for pixel in detector_data.vertices_raycast(f,off):
                col = pixel.to_column4()
                col = (mv @ col).to_vec4().to_vec3()
                x, y, z = col.unpack()
                #print(x, y, z)
                visible = (z > 0).all()
                if visible:
                    ralt,az = anti_altaz_represent(x,y,z)
                    axes.plot(ralt * np.sin(az), ralt * np.cos(az), color="black")
                    #axes.plot(x, y, color="black")

        axes.set_xlim(-90, 90)
        axes.set_ylim(-90, 90)
        horizon = Circle((0, 0), 90, edgecolor="black",facecolor="none")
        axes.add_patch(horizon)
        for radius in range(10,90,10):
            parallel = Circle((0, 0), radius, edgecolor="gray",facecolor="none")
            axes.add_patch(parallel)
        axes.set_aspect("equal")

    @classmethod
    def on_scene_mouse_event(cls, resources: ResourceStorage, event):
        if event.button in [1,3] and None not in [event.xdata, event.ydata]:
            add_mode = event.button==1
            print("LMB_HOLD")
            dat = scene_3d_view(resources)
            if dat is None:
                return False
            earth, observatory, detector = dat
            x = event.xdata
            y = event.ydata

            ralt = (x**2+y**2)**0.5*np.pi/180
            az = np.arctan2(x,y)
            direction = Vector3(np.sin(ralt)*np.sin(az),np.sin(ralt)*np.cos(az),np.cos(ralt)).normalized().to_column4()
            #direction = Vector3(x,y,1).normalized().to_column4()

            #vp_inv = get_vp_inv(observatory)
            view_inv = observatory.model_matrix()
            eci = (view_inv@direction).to_vec4().to_vec3()
            eci_x,eci_y,eci_z = eci.unpack()
            hor = (eci_x**2+eci_y**2)**0.5
            dec = np.arctan2(eci_z,hor)*180/np.pi
            ra = np.arctan2(eci_y,eci_x)*180/np.pi
            print("Query radec", ra,dec)
            stars = StarList.fetch_sql("SELECT * FROM stars WHERE dec>? and dec<?",[dec-5,dec+5])
            if stars.stars:
                v_eci = stars.pack_stars_eci()
                dots = v_eci.dot(eci)
                star = stars[np.argmax(dots)]
                angsep = np.arccos(np.max(dots))*180/np.pi
                print("Closest",star,angsep,np.max(dots),eci.length())
                if angsep < 1.0:
                    star_resource = resources.get_resource("star_list")
                    if add_mode:
                        star_resource.add_star(star.get_star_identifier())

                    return True
            return False
        return False


class DetectorScene(Scene):
    SceneName = "Detector"

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        detector_data = resources.try_get("detector")
        if detector_data is None:
            return
        detector_data:PadamoDetector

        star_list = resources.get_resource("star_list")
        chosen_stars = star_list.get_stars()

        if resources.has_resource("time_data"):
            time_data = resources.get("time_data")
            k = get_current_frame(resources,time_data)
            dt = time_data[k]
        else:
            dt = None
        dat = scene_3d_view(resources,dt=dt)
        if dat is None:
            return
        earth, observatory, detector = dat
        suitable_stars = get_stars()
        f = resources.get_resource("f").get_estimation()
        dx = resources.get_resource("plane_offset_x").get_estimation()
        dy = resources.get_resource("plane_offset_y").get_estimation()
        swap_x = Matrix([
            [-1,0,0,-dx],
            [ 0,1,0,-dy],
            [ 0,0,1,0],
            [ 0,0,0,1]
        ])
        vp = swap_x@get_vp(detector, f)
        x,y,z = transform_starvec(suitable_stars,vp)

        mags = np.array([x.vmag for x in suitable_stars])

        visible = z > 0
        s = 3 ** (5 - mags)

        def selection_color(x):
            if chosen_stars.contains(x):
                return "red"
            else:
                return "blue"

        print(len(suitable_stars.stars))
        c = [selection_color(v) for i, v in enumerate(suitable_stars.stars) if visible[i]]


        # Drawing FOV
        if resources.has_resource("time_data") and resources.has_resource("signal_data"):
            time_data = resources.get("time_data")
            signal_data = resources.get("signal_data")
            k = get_current_frame(resources,time_data)
            frame = signal_data[k]
            if resources.get("show_all_pixels") or not resources.has_resource("mask_3d"):
                alive_override = None
            else:
                print("Mask override")
                alive_override = resources.get("mask_3d")[k]
            lx, mx, ly, my = detector_data.draw(axes, frame,alive_override=alive_override)
            ts = datetime.utcfromtimestamp(time_data[k]).strftime('%Y-%m-%d %H:%M:%S')
            axes.set_title(ts)
        else:
            lx, mx, ly, my = detector_data.draw(axes, np.zeros(detector_data.compat_shape))


        # Sprinkling stars
        axes.scatter(x[visible], y[visible], s=s[visible], c=c)
        k = resources.get("frame_probe")
        star_list.draw_annotations(axes,k)
        star_list.scatter_stars(axes,k)

        axes.set_xlim(lx, mx)
        axes.set_ylim(ly, my)
        axes.set_aspect("equal")

    @classmethod
    def on_scene_mouse_event(cls, resources: ResourceStorage, event):
        return False




class StellarModel(ReconsructionModel):
    RequestedResources = ResourceRequest({
        "detector": dict(display_name="Detector", type_=DetectorResource),
        "signal_data": dict(display_name="Signal data", type_=HDF5Resource),
        "time_data": dict(display_name="Time data", type_=HDF5Resource),
        "pymc_sampling": dict(display_name="PyMC arguments", type_=PyMCSampleArgsResource),
        "time_probe": dict(display_name="Plot time", type_=TimeResource, category="Display"),
        "frame_probe": dict(display_name="Plot frame", default_value=0, category="Display"),
        "show_all_pixels": dict(display_name="Show all pixels", default_value=True, category="Display"),
        "latitude": dict(display_name="Latitude [°]", default_value=0.0),
        "longitude": dict(display_name="Longitude [°]", default_value=0.0),
        "amplitude": dict(display_name="Amplitude", default_value=template_exponent(0.1,False),
                          category="Priors"),
        "sigma_psf": dict(display_name="Sigma PSF [mm]", default_value=template_halfnormal(1.0,False),
                          category="Priors"),
        "sigma": dict(display_name="Sigma [mm]", default_value=template_halfnormal(1.0,False),
                          category="Priors"),
        "orientation": dict(display_name="Orientation", type_=OrientationPriorResource,
                  category="Priors"),
        "f": dict(display_name="Focal distance [mm]", default_value=template_normal(150.0,1.0),
                  category="Priors"),
        "plane_offset_x": dict(display_name="Focal plane offset X", default_value=ConstantMaker.template(0.0),
                               category="Priors"),
        "plane_offset_y": dict(display_name="Focal plane offset Y", default_value=ConstantMaker.template(0.0),
                               category="Priors"),
        "use_cauchy":dict(display_name="Use cauchy error", default_value=True,category="Priors"),
        "star_list": dict(display_name="Stars", type_=PinnedStars, category="Star selection")
        # "stars": dict(display_name="Stars", type_=StarListResource),
        # "pdm_width": dict(display_name="PDM width [pixels]", default_value=8),
        # "pdm_height": dict(display_name="PDM height [pixels]", default_value=8),
    })
    Scenes = [SkyScene,DetectorScene]

    @classmethod
    def calculate(cls, resources: ResourceStorage):
        if not resources.has_resource("signal_data"):
            return
        if not resources.has_resource("time_data"):
            return
        if not resources.has_resource("mask_3d"):
            return
        if not resources.has_resource("detector"):
            return
        detector_geometry = resources.get("detector")
        signal_data = resources.get("signal_data")

        #chosen_stars:StarList = resources.get("stars")

        times = resources.get("time_data")

        mask = resources.get("mask_3d")
        era = unixtime_to_era(times)

        with pm.Model() as model:
            # hour_angle = resources.get_resource("hour_angle").create_distribution("GHA") * np.pi / 180
            # declination = resources.get_resource("declination").create_distribution("dec") * np.pi / 180
            # own_rotation = resources.get_resource("own_rotation").create_distribution("Omega") * np.pi / 180
            orientation = resources.get_resource("orientation")
            amplitude = resources.get_resource("amplitude").create_distribution("amplitude")
            f = resources.get_resource("f").create_distribution("f")
            sigma_psf = resources.get_resource("sigma_psf").create_distribution("sigma_psf")
            sigma = resources.get_resource("sigma").create_distribution("sigma")
            earth, observatory,detector = scene_3d(resources, era, orientation.get_prior, backend=pm.math)
            p = projection_matrix(f)
            v = detector.view_matrix()
            dx = resources.get_resource("plane_offset_x").create_distribution("dX")
            dy = resources.get_resource("plane_offset_y").create_distribution("dY")
            neg_x = Matrix([
                [-1,0,0,-dx],
                [0,1,0,-dy],
                [0,0,1,0],
                [0,0,0,1]
            ])
            vp = neg_x @ p @ v

            chosen_stars, star_amplitudes = resources.get_resource("star_list").get_stars_with_amplitudes()

            estimations = []
            observed_data = []
            star_cache = dict()

            for pixel in detector_geometry.pixels:
                i = pixel.index
                mask_index = (slice(None),)+i
                mask_row = mask[mask_index]
                #print("Pixel time mask", mask_row)
                #print("Pixel mask shapes", mask.shape,mask_row.shape, mask_index)
                if mask_row.any():
                    min_x, max_x, min_y, max_y = pixel.get_bounds()
                    sum_intensity = None
                    for star_index in range(len(chosen_stars)):
                        star = chosen_stars[star_index]
                        key = star.get_star_identifier()
                        #print("STAR processing", star, chosen_stars)

                        ampl = star_amplitudes[star_index]

                        if key not in star_cache.keys():
                            eci = star.eci_direction.to_column4()
                            x1,y1,z1 = (vp@eci).to_vec4().to_vec3().unpack()
                            star_cache[key] = (x1,y1,z1,amplitude * ampl)
                        x,y,z,pre_e0 = star_cache[key]
                        x = x[mask_row]
                        y = y[mask_row]
                        z = z[mask_row]
                        e0 = pt.switch(z>0, pre_e0, 0.0)
                        track_v = e0*d_erf(min_x,max_x,x,sigma_psf)*d_erf(min_y,max_y,y,sigma_psf)
                        if sum_intensity is None:
                            sum_intensity = track_v
                        else:
                            sum_intensity = sum_intensity+track_v
                    obs = signal_data[mask_index][mask_row]
                    estimations.append(sum_intensity)
                    observed_data.append(obs)
                    print("Intermediate shape:", sum_intensity.shape.eval(), obs.shape)

            tensors = pt.concatenate(estimations)
            observed = np.concatenate(observed_data)
            print("Final shape test",tensors.shape.eval(),observed.shape)
            if resources.get("use_cauchy"):
                res = pm.Cauchy("likelyhood", alpha=tensors, beta=sigma, observed=observed)
            else:
                res = pm.Normal("likelyhood", mu=tensors, sigma=sigma, observed=observed)

            #model.profile(res).summary()
            trace = resources.get_resource("pymc_sampling").sample()
            resources.set("trace", trace)

    @LabelledAction("Select pixels")
    @staticmethod
    def select_pixels(resources):
        print("Selecting pixels...")
        if not resources.has_resource("detector") or not resources.has_resource("signal_data"):
            return
        signal = resources.get("signal_data")
        mask = np.full(fill_value=False,shape=signal.shape)
        for star_resource in resources.get_resource("star_list").data:
            print("Reading", star_resource)
            k,x,y = star_resource.pinpoint()
            x,y = resources.get("detector").find_pixel_id_in_position(np.array([x,y]))
            mask = np.logical_or(mask,flood_fill(signal>star_resource.data.get("threshold"),k,x,y))
        #print("GENERATED MASK", mask)
        resources.set("mask_3d",mask)

    @LabelledAction("Unselect pixels")
    @staticmethod
    def unselect_pixels(resources):
        print("Unselecting pixels...")
        if resources.has_resource("mask_3d"):
            resources.delete_resource("mask_3d")
