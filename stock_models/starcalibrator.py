import numpy as np
import pymc as pm
import pytensor.tensor as pt
from matplotlib import pyplot as plt

from RecoResources import ResourceStorage
from padamo_rs_detector_parser import PadamoDetector
from reco_prelude import ReconsructionModel, ResourceRequest, HDF5Resource, TimeResource, DetectorResource
from reco_prelude import template_normal, StarListResource, Scene
from transform import Transform, unixtime_to_era, Quaternion, Vector3, TransformBuilder, observatory_transform
from transform import ecef_align, projection_matrix, simple_projection_matrix, Vector4
from stars import StarList

# WORK IN PROGRESS

def scene_3d(resources,era,hour_angle, declination, own_rotation,backend=np):
    latitude = resources.get("latitude") * np.pi / 180.0
    longitude = resources.get("longitude") * np.pi / 180.0
    earth: Transform = TransformBuilder().with_rotation(Quaternion.rotate_xy(era)).build()

    # Make observatory and attach it to Earth.
    # Neglect position
    observatory:Transform = observatory_transform(latitude, longitude, apply_position=False)
    observatory.parent = earth
    detector:Transform = TransformBuilder() \
        .with_rotation(ecef_align(declination, hour_angle, own_rotation, backend=backend)) \
        .with_parent(earth)\
        .build()

    return earth, observatory, detector

def scene_3d_view(resources):
    hour_angle = resources.get_resource("hour_angle").get_estimation()
    declination = resources.get_resource("declination").get_estimation()
    own_rotation = resources.get_resource("own_rotation").get_estimation()
    # chosen_stars = resources.get("stars")
    f = resources.get_resource("f").get_estimation()
    if None in [hour_angle, declination, own_rotation, f]:
        return
    hour_angle *= np.pi / 180
    declination *= np.pi / 180
    own_rotation *= np.pi / 180

    dt = resources.get("time_probe").timestamp()
    era = unixtime_to_era(dt)
    return scene_3d(resources, era, hour_angle, declination, own_rotation)


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



def d_erf(a,b,mu,sigma):
    scale = sigma*2**0.5
    return (pm.math.erf((b-mu)/scale)-pm.math.erf((a-mu)/scale))/2.0

class SkyScene(Scene):
    SceneName = "Sky"

    @classmethod
    def draw_scene(cls, resources: ResourceStorage, fig: plt.Figure, axes: plt.Axes):
        chosen_stars = resources.get("stars")
        dat = scene_3d_view(resources)
        if dat is None:
            return
        earth, observatory, detector = dat
        suitable_stars = get_stars()
        vp = get_vp(observatory)
        x,y,z = transform_starvec(suitable_stars,vp)

        f = resources.get_resource("f").get_estimation()
        mags = np.array([x.vmag for x in suitable_stars])
        chosen_stars = resources.get("stars")

        visible = z > 0
        s = 3 ** (4 - mags)

        def selection_color(x):
            if chosen_stars.contains(x):
                return "red"
            else:
                return "blue"

        print(len(suitable_stars.stars))
        c = [selection_color(v) for i, v in enumerate(suitable_stars.stars) if visible[i]]
        axes.scatter(x[visible], y[visible], s=s[visible], c=c)

        # Drawing FOV
        detector_data = resources.try_get("detector")
        if detector_data is not None:
            detector_data: PadamoDetector
            model = detector.model_matrix()
            mvp = vp @ model
            for pixel in detector_data.vertices_raycast(f):
                col = pixel.to_column4()
                col = (mvp @ col).to_vec4().to_vec3()
                x, y, z = col.unpack()
                print(x, y, z)
                visible = (z > 0).all()
                if visible:
                    axes.plot(x, y, color="black")

        axes.set_xlim(-1, 1)
        axes.set_ylim(-1, 1)
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
            direction = Vector3(x,y,1).normalized().to_column4()

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
                    star_resource:StarList = resources.get("stars")
                    if add_mode:
                        if not star_resource.contains(star):
                            star_resource.append(star)
                        else:
                            return False
                    else:
                        star_resource.remove(star)
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

        chosen_stars = resources.get("stars")
        dat = scene_3d_view(resources)
        if dat is None:
            return
        earth, observatory, detector = dat
        suitable_stars = get_stars()
        f = resources.get_resource("f").get_estimation()
        vp = get_vp(detector, f)
        x,y,z = transform_starvec(suitable_stars,vp)

        mags = np.array([x.vmag for x in suitable_stars])
        chosen_stars = resources.get("stars")

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

        lx, mx, ly, my = detector_data.draw(axes, np.zeros(detector_data.compat_shape))

        axes.set_xlim(lx, mx)
        axes.set_ylim(ly, my)

        # Sprinkling stars
        axes.scatter(x[visible], y[visible], s=s[visible], c=c)

        axes.set_aspect("equal")

class StellarModel(ReconsructionModel):
    RequestedResources = ResourceRequest({
        "detector": dict(display_name="Detector", type_=DetectorResource),
        "signal_data": dict(display_name="Signal data", type_=HDF5Resource),
        "time_data": dict(display_name="Time data", type_=HDF5Resource),
        "time_probe": dict(display_name="Plot time", type_=TimeResource),
        "latitude": dict(display_name="Latitude [°]", default_value=0.0),
        "longitude": dict(display_name="Longitude [°]", default_value=0.0),
        "hour_angle": dict(display_name="Hour angle [°]", default_value=template_normal(0.0, 1.0)),
        "declination": dict(display_name="Declination [°]", default_value=template_normal(0.0, 1.0)),
        "own_rotation": dict(display_name="Own rotation [°]", default_value=template_normal(0.0, 1.0)),
        "f": dict(display_name="Focal distance [mm]", default_value=template_normal(150.0,1.0)),
        "stars": dict(display_name="Stars", type_=StarListResource),
        "pdm_width": dict(display_name="PDM width [pixels]", default_value=8),
        "pdm_height": dict(display_name="PDM height [pixels]", default_value=8),
    })
    Scenes = [SkyScene,DetectorScene]

    @classmethod
    def calculate(cls, resources: ResourceStorage):
        signal_data = resources.get("signal_data")

        latitude = resources.get("latitude") * np.pi / 180.0
        longitude = resources.get("longitude") * np.pi / 180.0
        chosen_stars:StarList = resources.get("stars")

        times = resources.get("time_data")
        era = unixtime_to_era(times)

        with pm.Model() as model:
            hour_angle = resources.get_resource("hour_angle").create_distribution("GHA") * np.pi / 180
            declination = resources.get_resource("declination").create_distribution("dec") * np.pi / 180
            own_rotation = resources.get_resource("own_rotation").create_distribution("Omega") * np.pi / 180
            f = resources.get_resource("f").create_distribution("f")
            earth, observatory,detector = scene_3d(resources, era, hour_angle, declination, own_rotation,
                                                   backend=pm.math)
            p = projection_matrix(f)
            v = detector.view_matrix()
            vp = p @ v

            for star in chosen_stars:
                eci = star.eci_direction.to_column4()
                x,y,z = (vp@eci).to_vec4().to_vec3().unpack()
                if z>0:
                    e0 = 1.0 #TODO calculate E0 from stellar data


            # # Shapes are matching "eras" and "times" shape
            # x, y, z = transform_starvec(chosen_stars, vp)
            # visible = z > 0
