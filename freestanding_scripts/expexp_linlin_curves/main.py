#!/usr/bin/env python3

import json, base64, io, tempfile, shutil

import numpy as np
import matplotlib.pyplot as plt
import pymc as pm
import arviz as az
from arviz.data.inference_data import  InferenceData
import matplotlib.ticker as ticker

from padamo_rs_detector_parser import PadamoDetector


az.rcParams['data.load'] = 'eager'

# EXP_DATA = "model_ExpAExp_Phi30_U20_GAP.json"
# LIN_DATA = "model_LinALin_Phi30_U20_GAP.json"

EXP_DATA = "model_ExpAExp_Phi30_U20_GAP_T80_450.json"
LIN_DATA = "model_LinALin_Phi30_U20_GAP_T80_450.json"

MA_FILTER=3
ACTIVE_WINDOW=100


# GRID BASED COLORATION
def hsv_to_rgb(h,s,v):
    '''
    0<=h<=360
    0<=s<=1
    0<=v<=1
    '''
    h = h % 360
    c = v*s
    x = c*(1-abs((h/60)%2-1))
    m = v-c
    if h<60:
        _r = c; _g = x; _b = 0
    elif h<120:
        _r = x
        _g = c
        _b = 0
    elif h<180:
        _r = 0
        _g = c
        _b = x
    elif h<240:
        _r = 0
        _g = x
        _b = c
    elif h<300:
        _r = x
        _g = 0
        _b = c
    else:
        _r = c
        _g = 0
        _b = x
    return _r+m, _g+m, _b+m


def h_color(i, hue_shift=0.0,s_shift = 0.0, v_shift = 0.0):
    h = (i)/8*360+hue_shift
    s = 1-s_shift
    v = 1-v_shift
    return hsv_to_rgb(h,s,v)

WIDTH = 16
HEIGHT = 16


def floormod(x,y):
    pivot = int(np.floor(x/y))*y
    return x-pivot

def get_color(i,j):
    if i%2==0:
        j1 = j
    else:
        j1 = j + 1
    shift_id = floormod(floormod(i-j1*WIDTH//4,WIDTH),WIDTH)
    gray_shift = 0.0
    if j%2==0 and (i-j//2)%2==0:
        gray_shift = 1.0
    return h_color(shift_id,j/HEIGHT*180,
                   v_shift=gray_shift*0.5,
                   s_shift=gray_shift*0.3)


def get_color_from_index(index):
    return get_color(index[0],index[1])


def load_b64_array(entry):
    bytes_array = base64.b64decode(entry["data"].encode('ascii'))
    compressed_array = io.BytesIO()
    compressed_array.write(bytes_array)
    compressed_array.seek(0)
    arr = np.load(compressed_array)["arr_0"]
    return arr

def load_detector(entry):
    v = entry["data"]
    detector = PadamoDetector(v["detector"])
    detector.alive_pixels = np.array(v["alive_pixels"])
    return detector


def load_trace(entry):
    tempdir = tempfile.mkdtemp()
    tgt_file = tempdir+"/data.nc"
    with open(tgt_file,"wb") as fp:
        decoded = base64.b64decode(entry["data"].encode("ascii"))
        fp.write(decoded)
    trace = InferenceData.from_netcdf(tgt_file)
    shutil.rmtree(tempdir)
    return trace

def plot_exp_curve(axes, expdata):
    print(expdata.keys())

    exp_trace = load_trace(expdata["trace"]).posterior
    print(exp_trace)
    k0 = expdata["k0"]["data"]
    pivot = k0+float(np.median(exp_trace["lc_offset"]))
    e0 = float(np.median(exp_trace["e0"]))
    tau1 = float(np.median(exp_trace["lc_left_tau"]))
    tau2 = float(np.median(exp_trace["lc_right_tau"]))
    k1 = expdata["k_start"]["data"]
    k2 = expdata["k_end"]["data"]

    lc_xs = np.arange(k1,k2,0.1)
    lc_xs_off = lc_xs-pivot
    left_lc = np.exp(lc_xs_off/tau1)
    right_lc = np.exp(-lc_xs_off/tau2)
    lc = np.minimum.reduce([left_lc,right_lc])
    axes.plot(lc_xs,lc*e0, "-",linewidth=2.0, color="red")


def plot_lin_curve(axes, lindata):
    print(lindata.keys())

    lin_trace = load_trace(lindata["trace"]).posterior
    print(lin_trace)


    k0 = lindata["k0"]["data"]
    pivot = k0+float(np.median(lin_trace["lc_offset"]))
    e0 = float(np.median(lin_trace["e0"]))
    tau1 = float(np.median(lin_trace["lc_left_tau"]))
    tau2 = float(np.median(lin_trace["lc_right_tau"]))
    k1 = lindata["k_start"]["data"]
    k2 = lindata["k_end"]["data"]

    lc_xs = np.arange(k1,k2,0.1)
    lc_xs_off = lc_xs-pivot

    left_lc = 1+lc_xs_off/tau1
    right_lc = 1-lc_xs_off/tau2

    lc = np.minimum.reduce([left_lc,right_lc])
    lc = np.where(lc>0,lc,0)
    axes.plot(lc_xs,lc*e0, "-",linewidth=2.0, color="green")

def plot_detector(axes,detector,kin_data):
    minx, maxx, miny, maxy = detector.draw_colors(axes, get_color_from_index)
    print(minx, maxx, miny, maxy)
    axes.set_ylim(miny,maxy)
    axes.set_xlim(2,maxx)
    axes.xaxis.set_major_locator(ticker.NullLocator())
    axes.yaxis.set_major_locator(ticker.NullLocator())

    kinematics_data_trace = load_trace(kin_data["trace"]).posterior
    x0 = float(np.median(kinematics_data_trace["X0"]))
    y0 = float(np.median(kinematics_data_trace["Y0"]))
    k0 = kin_data["k0"]["data"]
    k1 = kin_data["k_start"]["data"]
    k2 = kin_data["k_end"]["data"]
    u0 = float(np.median(kinematics_data_trace["u0"]))
    phi0 = float(np.median(kinematics_data_trace["phi0"]))*np.pi/180
    w = float(np.median(kinematics_data_trace["sigma_psf"]))
    ts = np.array([k1,k2])
    xs = x0 + u0*np.cos(phi0)*(ts-k0)
    ys = y0 + u0*np.sin(phi0)*(ts-k0)
    axes.arrow(x=xs[0],y=ys[0],dx=xs[1]-xs[0],dy=ys[1]-ys[0],color="red",length_includes_head=True,width=w)

if __name__=="__main__":
    with open(EXP_DATA,"r") as fp:
        expdata = json.load(fp)

    with open(LIN_DATA,"r") as fp:
        lindata = json.load(fp)

    assert expdata["reco_data"]==lindata["reco_data"]
    #assert expdata["detector"]==lindata["detector"]

    data = load_b64_array(expdata["reco_data"])
    detector = load_detector(expdata["detector"])

    xs = np.arange(data.shape[0])

    fig, axes = plt.subplots(figsize=(10,8))

    accum = []
    metrics = []
    colors = []

    w = MA_FILTER
    active_win = ACTIVE_WINDOW
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
            colors.append(get_color_from_index(i))
    accum = np.array(accum)
    order = np.argsort(metrics)
    axes.stackplot(xs,accum[order],colors=colors)


    # EXP-A-EXP curve
    plot_exp_curve(axes,expdata)


    # LIN-A-LIN curve

    plot_lin_curve(axes,lindata)

    axes.set_ylim(-2,52)
    axes.set_xlabel("T, ms", fontsize=30)
    axes.set_ylabel("Signal, a. u.", fontsize=30)

    axes.tick_params(axis='x', labelsize=20)
    axes.tick_params(axis='y', labelsize=20)

    # INCUT PIXELMAP
    W_BIG = 24.8-2
    H_BIG = 24.8*2

    h = 0.6
    w = h/H_BIG*W_BIG

    axes_inset = axes.inset_axes([0.0, 0.4, w, h])
    axes_inset.set_aspect("equal")
    plot_detector(axes_inset,detector,expdata)

    fig.tight_layout()
    fig.savefig("two_lc.png")
    fig.savefig("two_lc.pdf")
