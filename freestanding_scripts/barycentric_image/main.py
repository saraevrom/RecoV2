#!/usr/bin/env python3

import json

import matplotlib.pyplot as plt
import h5py
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

import config
from padamo_rs_detector_parser import PadamoDetector, FixedNorm

def save_fig(fig,name):
    fig.tight_layout()
    fig.savefig(name+".png")
    fig.savefig(name+".pdf")

def bayes_trajectory(phi_offset=0.0,t1=config.BAYES_START,t2=config.BAYES_END):
    ts = np.array([t1, t2])
    phi0 = (config.BAYES_PHI0+phi_offset)*np.pi/180
    xs = config.BAYES_X0 + config.BAYES_U0*np.cos(phi0)*(ts - config.BAYES_K0)
    ys = config.BAYES_Y0 + config.BAYES_U0*np.sin(phi0)*(ts - config.BAYES_K0)
    return ts,xs,ys


def fonts_bigger(ax):
    ax.tick_params(axis='x', labelsize=15)
    ax.tick_params(axis='y', labelsize=15)


def fig_11(ax):
    fonts_bigger(ax)
    with h5py.File("MET192328_221212.h5") as fp:
        track_data = np.array(fp["pdm_2d_rot_global"])

    frame = np.max(track_data, axis=0)
    print(np.min(frame), np.max(frame))

    ax.tick_params(top=True, labeltop=True, bottom=False, labelbottom=False)
    ax.set_aspect("equal")
    minx, maxx, miny, maxy = detector.draw(ax, frame, norm=FixedNorm(3.0, np.max(frame)))

    ax.set_xlim(minx,maxx)
    ax.set_ylim(miny,-2.0)

    del frame
    del track_data

    bary = pd.read_csv("trajectory.tsv", sep="\t")
    plt.plot(bary["x"],bary["y"],"-",color="black",zorder=3)
    plt.plot(bary["x"][::10],bary["y"][::10],"o",color="black",zorder=3)

    ts,xs,ys = bayes_trajectory()
    ax.arrow(xs[0],ys[0],xs[1]-xs[0],ys[1]-ys[0],color="red",width=0.3,alpha=0.9,length_includes_head=True,zorder=2)


    _,xs_rad,ys_rad = bayes_trajectory(-1.5,t1=-500,t2=config.BAYES_K0)
    ax.plot(xs_rad,ys_rad,"-",color="green",zorder=1)



def fig_12(ax):
    fonts_bigger(ax)

    bary = pd.read_csv("trajectory.tsv", sep="\t")
    # ax.plot(bary["x"],bary["y"],"-",color="black",zorder=3)
    # ax.plot(bary["x"][::10],bary["y"][::10],"o",color="black",zorder=3)
    ts,xs,ys = bayes_trajectory()

    ax.plot(bary["t"], bary["x"],color="black")
    ax.plot(bary["t"][::10], bary["x"][::10],"o",color="black")
    ax.plot(ts, xs,color="red")

    def linreg(x,k,b):
        return k*x+b
    popt,pcov = curve_fit(linreg,bary["t"],bary["x"],p0=np.array([1.0,0.0]))
    ax.plot(bary["t"], linreg(bary["t"],*popt),"--",color="black")
    ax.set_xlabel("T, ms", fontsize=15)
    ax.set_ylabel("X, mm", fontsize=15)

if __name__=="__main__":
    with open(config.DETECTOR_PATH, "r") as fp:
        detector = PadamoDetector(json.load(fp))



        #Figure 1.1: trace
        fig,ax = plt.subplots(figsize=(8,4),dpi=250)
        fig_11(ax)
        save_fig(fig,"Fig1_trace")

        #Figure 1.2: X(t)
        fig,ax = plt.subplots()
        fig_12(ax)
        save_fig(fig,"Fig1_coord")

        #Figure 1 combo
        # fig,(ax1,ax2) = plt.subplots(1,2)
        # fig_11(ax1)
        # fig_12(ax2)
        # save_fig(fig,"Fig1_all")
