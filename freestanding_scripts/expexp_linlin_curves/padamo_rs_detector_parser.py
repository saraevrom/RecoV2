import os.path
from typing import Tuple
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps
from matplotlib.patches import Polygon
from transform.vectors import Vector2, Vector3

VIRIDIS = colormaps["viridis"]

BASE_PATH = os.path.dirname(os.path.realpath(__file__))

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate


@static_vars(xs=None,ys=None,ws=None)
def get_quadrature_rules():
    if get_quadrature_rules.xs is None:
        get_quadrature_rules.xs, get_quadrature_rules.ys = np.genfromtxt(os.path.join(BASE_PATH, "quadrature_xy_small.txt")).T
        get_quadrature_rules.ws = np.genfromtxt(os.path.join(BASE_PATH, "quadrature_w_small.txt"))
    return get_quadrature_rules.xs, get_quadrature_rules.ys, get_quadrature_rules.ws


def unit_triangle_integral(f,backend=np):
    quadrature_x, quadrature_y, quadrature_w = get_quadrature_rules()
    return 0.5*backend.sum(quadrature_w*f(quadrature_x,quadrature_y), axis=-1)


def unit_triangle_integral_array(f,backend=np):
    quadrature_x, quadrature_y = np.genfromtxt("quadrature_xy.txt").T
    quadrature_w = np.genfromtxt("quadrature_w.txt")
    return 0.5*backend.sum(quadrature_w*f(quadrature_x,quadrature_y))


def arbitrary_triangle_integral(f,r1:Tuple[float,float],r2:Tuple[float,float],r3:Tuple[float,float],backend=np):
    def offset_func(s,t):
        x = r1[0] + (r2[0]-r1[0]) * s + (r3[0]-r1[0]) * t
        y = r1[1] + (r2[1]-r1[1]) * s + (r3[1]-r1[1]) * t
        return f(x, y)

    j = abs((r2[0]-r1[0])*(r3[1]-r1[1]) - (r2[1]-r1[1])*(r3[0]-r1[0]))
    return j*unit_triangle_integral(offset_func,backend=backend)

class PlotNorm(object):
    def get_minmax(self, data, alive_pixel_matrix):
        raise NotImplementedError

class AutoscaleNorm(PlotNorm):
    def get_minmax(self, data, alive_pixel_matrix):
        #print(data.shape, alive_pixel_matrix.shape)
        if not alive_pixel_matrix.any():
            return 0.0,0.001
        r = data[alive_pixel_matrix]
        return np.min(r), np.max(r)

class FixedNorm(PlotNorm):
    def __init__(self,min_, max_):
        self.min_ = min_
        self.max_ = max_

    def get_minmax(self, data, alive_pixel_matrix):
        return self.min_, self.max_



def altmin(a,b):
    if a is None:
        return b
    if b is None:
        return a
    return min(a,b)


def altmax(a,b):
    if a is None:
        return b
    if b is None:
        return a
    return max(a,b)


def earclip_generator(vertices):
    vertices = list(vertices)
    while len(vertices)>3:
        i = 0
        while i<len(vertices):
            a = Vector2(*vertices[i-1])
            b = Vector2(*vertices[i])
            c = Vector2(*vertices[(i+1) % len(vertices)])
            va = a-b
            vc = c-a
            if vc.cross(va) > 0.0:
                vertices.pop(i)
                yield [a.to_numpy(), b.to_numpy(), c.to_numpy()]
                break
            else:
                i+=1
    yield vertices

class PadamoPixel(object):
    def __init__(self,data:dict):
        self.index = tuple(data["index"])
        self.vertices = np.array(data["vertices"])
        self.min_x = np.min(self.vertices[:,0])
        self.max_x = np.max(self.vertices[:,0])
        self.min_y = np.min(self.vertices[:,1])
        self.max_y = np.max(self.vertices[:,1])

    def draw_pixel(self,ax:plt.Axes,source_array:np.ndarray,min_,max_,colormap,offset,alive_matrix):
        value = float(source_array[self.index])
        normalized = (value-min_)/(max_-min_)
        if normalized < 0.0:
            normalized = 0.0
        if normalized > 1.0:
            normalized = 1.0
        if alive_matrix[self.index]:
            color = colormap(normalized)
        else:
            color = "black"

        return self.draw_patch(ax,color,offset)
        # poly = Polygon(self.vertices+offset,color=color)
        # ax.add_patch(poly)
        # return self.min_x,self.max_x,self.min_y,self.max_y

    def draw_patch(self,ax:plt.Axes,color,offset,draw_border=False):
        add_kwargs = dict()
        if draw_border:
            add_kwargs["lw"] = 1.0
            add_kwargs["edgecolor"] = "black"
        poly = Polygon(self.vertices+offset,facecolor=color,fill=True,**add_kwargs)
        ax.add_patch(poly)
        return self.min_x,self.max_x,self.min_y,self.max_y

    def get_bounds(self):
        return self.min_x, self.max_x, self.min_y, self.max_y

    def integrate(self, f,backend=np):
        integral = None
        for triangle in self.triangles():
            n = arbitrary_triangle_integral(f, *triangle,backend=backend)
            if integral is None:
                integral = n
            else:
                integral = integral+n
        return integral

    def triangles(self):
        return earclip_generator(self.vertices)

    def position_is_inside(self,point:np.ndarray):
        for a,b,c in self.triangles():
            if point_in_triangle(point,a,b,c):
                return True
        return False

    def vertices_raycast(self, f):
        '''
        Creates directions for its vertices
        :param f: focal distance
        :return:
        '''
        xs = self.vertices[:,0]
        ys = self.vertices[:,1]

        # Clone first element
        xs = np.append(xs,xs[0])
        ys = np.append(ys,ys[0])

        zs = np.full((len(self.vertices)+1,),f)
        vec = Vector3(xs,ys,zs).normalized()
        return vec


def tri_sign(p1,p2,p3):
    p31 = p1-p3
    p32 = p2-p3
    return p31[0]*p32[1]-p31[1]*p32[0]

def point_in_triangle(pt,v1,v2,v3):
    d1 = tri_sign(pt,v1,v2)
    d2 = tri_sign(pt,v2,v3)
    d3 = tri_sign(pt,v3,v1)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def index_iterator(shape):
    if len(shape) != 0 and (np.array(shape) != 0.0).all():
        current_value = [0]*len(shape)
        yield tuple(current_value)
        #print(current_value)
        i = 0
        while i<len(shape):
            if current_value[i]<shape[i]-1:
                current_value[i] += 1
                i = 0
                yield tuple(current_value)
                #print(current_value)
            else:
                current_value[i] = 0
                i += 1


class PadamoDetector(object):
    def __init__(self,data:dict):
        self.name = data["name"]
        self.compat_shape = tuple(data["compat_shape"])
        self.pixels = [PadamoPixel(pixel) for pixel in data["content"]]
        self.json_data = data
        self.alive_pixels = np.full(self.compat_shape,True)

    def draw_blank(self,ax,alive_override=None):
        return self.draw(ax,np.zeros(self.compat_shape),alive_override=alive_override)

    def draw(self,ax:plt.Axes,plot_data:np.ndarray,norm:PlotNorm=AutoscaleNorm(), colormap=VIRIDIS, offset=(0,0), alive_override=None):
        if plot_data.shape != self.compat_shape:
            raise ValueError(f"Data has incompatible shape {plot_data.shape} (detector shape: {self.compat_shape})")
        min_, max_ = norm.get_minmax(plot_data,self.alive_pixels)
        if max_ <= min_:
            max_ = min_+0.01

        minx,maxx,miny,maxy = None,None,None,None
        if alive_override is None:
            alive = self.alive_pixels
        else:
            alive = alive_override
        for pixel in self.pixels:
            a,b,c,d = pixel.draw_pixel(ax,plot_data,min_,max_,colormap,offset,alive)
            minx = altmin(a,minx)
            maxx = altmax(b,maxx)
            miny = altmin(c,miny)
            maxy = altmax(d,maxy)

        return minx, maxx, miny, maxy

    def draw_colors(self,ax,color_indexer,unactive_color="white", offset=(0,0)):
        minx,maxx,miny,maxy = None,None,None,None
        for pixel in self.pixels:
            if self.pixel_is_active(pixel.index):
                color = color_indexer(pixel.index)
            else:
                color = unactive_color

            a,b,c,d = pixel.draw_patch(ax,color,offset, draw_border=True)
            minx = altmin(a,minx)
            maxx = altmax(b,maxx)
            miny = altmin(c,miny)
            maxy = altmax(d,maxy)
        return minx, maxx, miny, maxy


    def index_at(self,point):
        point = np.array(point)
        for pixel in self.pixels:
            if pixel.position_is_inside(point):
                return pixel.index
        return None

    def toggle_pixel(self,i):
        self.alive_pixels[i] = not self.alive_pixels[i]

    def set_pixel_active(self,i,v):
        if self.alive_pixels[i] != v:
            self.alive_pixels[i] = v
            return True
        return False

    def iterate(self):
        return index_iterator(self.compat_shape)

    def pixel_is_active(self,i):
        return self.alive_pixels[i].any()

    def get_active_bounds(self, alive_override=None):
        minx, maxx, miny, maxy = None, None, None, None
        if alive_override is None:
            alive = self.alive_pixels
        else:
            alive = alive_override
        for pixel in self.pixels:
            if alive[pixel.index]:
                a, b, c, d = pixel.get_bounds()
                minx = altmin(a, minx)
                maxx = altmax(b, maxx)
                miny = altmin(c, miny)
                maxy = altmax(d, maxy)
        return minx, maxx, miny, maxy

    def vertices_raycast(self,f:float):
        '''
        Makes direction vectors for pixels
        :param f:
        :return:
        '''
        return [pixel.vertices_raycast(f) for pixel in self.pixels]
