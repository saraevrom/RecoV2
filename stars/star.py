import os.path

import sqlite3
from typing import Tuple, List
from transform import Vector3

import numpy as np


def connect_db():
    dirpath = os.path.dirname(os.path.realpath(__file__))
    # BSC5_PM = Bright Star Catalog 5 Photometric data
    filepath = os.path.join(dirpath,"bsc5_pm.db")
    return sqlite3.connect(filepath)


def make_where(kwargs:dict):
    predicates = []
    args = []
    for k in kwargs.keys():
        predicates.append(f"{k}=?")
        args.append(kwargs[k])
    return " AND ".join(predicates),args

def make_required(keys):
    r = []
    for k in keys:
        r.append(f"{k} IS NOT NULL")
    return " AND ".join(r)


def pair(a,b):
    if a and b:
        return a+" AND "+b
    if a and not b:
        return a
    if b and not a:
        return b
    else:
        return ""

class Star(object):
    def __init__(self,hr,hd,proper,bayer,flam,cons,ads,ads_comp,ra,dec,vmag,bv,ub,ri,n_vmag,u_vmag,u_bv,u_ub,n_ri):
        # From database
        self.hr = hr
        self.proper = proper
        self.hd = hd
        self.bayer = bayer
        self.flam = flam
        self.cons = cons
        self.ads = ads
        self.ads_comp = ads_comp
        self.ra = ra
        self.dec = dec
        self.vmag = vmag
        self.bv = bv
        self.ub = ub
        self.ri=ri
        self.n_vmag = n_vmag
        self.u_vmag = u_vmag
        self.u_bv = u_bv
        self.u_ub = u_ub
        self.n_ri = n_ri

    def __eq__(self, other):
        return self.hr == other.hr

    def get_star_identifier(self):
        if self.proper is not None:
            return f"{self.proper}"
        elif self.cons is None:
            return f"HR{self.hr}"
        elif self.bayer is not None:
            return f"{self.bayer} {self.cons}"
        elif self.flam is not None:
            return f"{self.flam} {self.cons}"
        # elif self.hd is not None:
        #     return f"Star HD{self.hd}"
        else:
            return f"HR{self.hr}"

    def __repr__(self):
        return f"Star {self.get_star_identifier()}"

    @property
    def eci_direction(self):
        if self.ra is not None and self.dec is not None:
            dec = self.dec*np.pi/180
            ra = self.ra*np.pi/180
            x = np.cos(dec) * np.cos(ra)
            y = np.cos(dec) * np.sin(ra)
            z = np.sin(dec)
            return Vector3(x, y, z)
        else:
            return None

    @property
    def bmag(self):
        if self.vmag is not None and self.bv is not None:
            return self.vmag+self.bv
        else:
            return None

    @property
    def umag(self):
        bmag = self.bmag
        if bmag is not None and self.ub is not None:
            return bmag+self.ub
        else:
            return None

    @classmethod
    def from_db_entry(cls, entry: Tuple):
        return cls(*entry)

    @staticmethod
    def fetch_sql(request,params, error_msg=None):
        conn = connect_db()
        entry = conn.execute(request, params).fetchone()
        if entry is None:
            if error_msg:
                raise ValueError(error_msg)
            else:
                return None
        return Star.from_db_entry(entry)

    @staticmethod
    def fetch_bayer(letter, cons):
        '''
        Get star in bayer notation
        :param letter: Bayer identifier (e.g. Alp, Bet, Gam...)
        :param cons: Constellation in 3 letters
        :return:
        '''
        return Star.fetch_sql("SELECT * FROM stars WHERE bayer=? AND constellation=?",
                              [letter,cons],
                              f"Star {letter} {cons} is not found")

    @staticmethod
    def fetch_hr(num):
        '''
        Fetch star by HR number
        '''
        return Star.fetch_sql("SELECT * FROM stars WHERE hr=?",
                              [num],
                              f"Star HR{num} is not found")

    @staticmethod
    def fetch_hd(num):
        '''
        Fetch star by HD number
        '''
        return Star.fetch_sql("SELECT * FROM stars WHERE hd=?",
                              [num],
                              f"Star HD{num} is not found")




    @staticmethod
    def fetch_proper(name):
        '''
        Fetch star by its name
        :param name: Star name
        :return:
        '''
        return Star.fetch_sql("SELECT * FROM stars WHERE proper=?",
                              [name],
                              f"Star {name} is not found")


class StarList(object):
    def __init__(self, stars:List[Star]):
        self.stars = stars

    @classmethod
    def new_empty(cls):
        return cls([])

    def __repr__(self):
        return f"Stars({repr(self.stars)})"

    def append(self, a):
        if a not in self.stars:
            self.stars.append(a)

    def remove(self,s):
        if s in self.stars:
            self.stars.remove(s)

    def __getitem__(self, item):
        return self.stars[item]

    def __setitem__(self, key, value):
        self.stars[key] = value

    def __len__(self):
        return len(self.stars)

    @classmethod
    def fetch_filtered(cls,required_keys=None,**kwargs):
        if required_keys is None:
            required_keys = []
        if not kwargs and not required_keys:
            return cls.fetch_all_stars()
        else:
            wh,args = make_where(kwargs)
            req_wh = make_required(required_keys)
            wh = pair(wh,req_wh)
            request = f"SELECT * FROM stars WHERE {wh}"
            #print(request,args)
            return cls.fetch_sql(request,args)


    @classmethod
    def fetch_sql(cls,request,args):
        conn = connect_db()
        entries = conn.execute(request, args).fetchall()
        return StarList([Star.from_db_entry(x) for x in entries])

    def pack_stars_eci(self) -> Vector3:
        '''
        Pack ECI of stars into one Vector3
        :param stars: star list
        :param add_data: Additional requested data
        :return:
        '''
        x = []
        y = []
        z = []
        for s in self.stars:
            eci = s.eci_direction
            if eci is not None:
                x.append(eci.x)
                y.append(eci.y)
                z.append(eci.z)
        return Vector3(np.array(x), np.array(y), np.array(z))

    @staticmethod
    def from_str(s):
        from .star_parser import parse_stars
        return parse_stars(s)

    @staticmethod
    def fetch_all_stars():
        '''
        Fetch all available stars
        :return:
        '''
        return StarList.fetch_sql("SELECT * FROM stars", [])

    def contains(self,star):
        return star in self.stars
