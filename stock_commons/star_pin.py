import numpy as np

from RecoResources import CombineResource, ResourceRequest, ArrayResource, StringResource, ResourceStorage
from stars import StarList, Star
from stars.star_parser import parse_one_star
import numba as nb



class StarEntry(StringResource):

    @classmethod
    def validate(cls,value):
        #print("Validate called")
        star = parse_one_star(value)
        #print("STAR:",value,star)
        if star is None:
            return False
        umag = star.umag
        return umag is not None

    @classmethod
    def try_from(cls, x):
        # To prohibit its creation from any string
        return None

class StarPinResource(CombineResource):
    Fields = ResourceRequest({
        "star_id": dict(display_name="Star",type_=StarEntry, default_value="Sirius"),
        "fixed_frame": dict(display_name="Fixed frame", default_value=0),
        "fixed_x0": dict(display_name="Fixed X [mm]", default_value=0.0),
        "fixed_y0": dict(display_name="Fixed Y [mm]", default_value=0.0),
        "threshold": dict(display_name="Signal threshold", default_value=1.0)
    })

    def get_star(self):
        identifier = self.data.get("star_id")
        star = parse_one_star(identifier)
        if star is None:
            raise ValueError(f"Star {identifier} is not valid")
        return star

    @classmethod
    def from_star(cls, star_id):
        if not StarEntry.validate(star_id):
            return None
        data = ResourceStorage()
        data.set_resource("star_id", StarEntry(star_id))
        data.set("fixed_frame",0)
        data.set("fixed_x0", 0.0)
        data.set("fixed_y0", 0.0)
        return cls(data)

    def draw_annotation(self,ax):
        xi,yi = self.scatter_point()
        ax.annotate(self.data.get("star_id"),
                    xy=(xi, yi), xycoords='data',
                    xytext=(1.5, 1.5), textcoords='offset points')

    def scatter_point(self):
        xi = self.data.get("fixed_x0")
        yi = self.data.get("fixed_y0")
        return [xi, yi]

    def pinpoint(self):
        ti = self.data.get("fixed_frame")
        xi = self.data.get("fixed_x0")
        yi = self.data.get("fixed_y0")
        return ti, xi, yi

def deduplicate(arr:list):
    i = 0
    while i<len(arr):
        alive = True
        for j in range(i+1,len(arr)):
            if arr[i]==arr[j]:
                arr.pop(i)
                alive = False
                break
        if alive:
            i += 1
    return arr

class PinnedStars(ArrayResource):
    InnerType = StarPinResource
    ITEM_LABEL = "Star #{}"

    def get_stars(self):
        a = [item.get_star() for item in self.data]
        a = deduplicate(a)
        return StarList(a)

    def add_star(self,star_id):
        parsed_star = parse_one_star(star_id)
        if parsed_star is None:
            return
        stars = self.get_stars()
        if parsed_star not in stars:
            self.append(StarPinResource.from_star(star_id))

    def draw_annotations(self, ax, k):
        for star in self.data:
            if k == star.data.get("fixed_frame"):
                star.draw_annotation(ax)

    def scatter_stars(self,ax,k):
        arr = []
        for star in self.data:
            if k == star.data.get("fixed_frame"):
                arr.append(star.scatter_point())
        if arr:
            xs, ys = np.array(arr).T
            ax.scatter(xs,ys,marker="+",color="green")
