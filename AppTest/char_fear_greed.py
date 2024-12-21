from tkinter import *
import tkinter as tk
import matplotlib.pyplot as plt
import math
import numpy as np
import requests, csv, json, urllib
from fake_useragent import UserAgent
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.projections import PolarAxes
import mpl_toolkits.axisartist.angle_helper as angle_helper
import mpl_toolkits.axisartist.floating_axes as floating_axes
from mpl_toolkits.axisartist.grid_finder import (DictFormatter, FixedLocator, MaxNLocator)
from rutinas import *


def setup_axes():
    """
    With custom locator and formatter.
    Note that the extreme values are swapped.
    """

    def xy_color(score=None):
        color = 'red' if score > 60 else 'green'
        angle = math.radians(((100 - score) / 100) * 180)
        x, y = math.cos(angle), math.sin(angle)
        return x, y, color

    def fear_vix(fear=None):
        hoy = datetime.now().date()
        BASE_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/"
        START_DATE = hoy.strftime("%Y-%m-%d")
        ua = UserAgent()

        headers = {
            'User-Agent': ua.random,
        }

        r = requests.get(BASE_URL + START_DATE, headers=headers)
        data = r.json()
        wfear = data['fear_and_greed']['score'] if is_none(fear) else fear
        vix = data['market_volatility_vix']['score']
        return wfear, vix

    def char_plot(ax=None, x=None, y=None, score=None, color=None, titulo=None):
        face = 'Gold' if (score > 45) and (score < 60) else 'GreenYellow' if score < 45 else 'OrangeRed'
        acolor = 'green' if face == 'Gold' else 'yellow'
        ax.set_facecolor(face)

        ax.arrow(0, 0, x, y, head_width=0.2, head_length=1.0, fc=acolor, ec='black', alpha=0.5)

        ax.text(0, -0.25, titulo, ha='center', va='center', fontsize=10, color='white')

        ax.text(0, 0.30, '{:.0f}'.format(score), ha='center', va='center', fontsize=28, color=acolor)

        ax.text(0.15, 0.25, ix[0], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=66)
        ax.text(0.27, 0.60, ix[1], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=40)
        ax.text(0.50, 0.75, ix[2], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=0)
        ax.text(0.72, 0.60, ix[3], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=-40)
        ax.text(0.85, 0.23, ix[4], transform=ax.transAxes, fontsize='x-small', color='black', alpha=0.7,
                ha='center', va='center', rotation=-66)

    # Crear el gráfico
    fg.clear()
    tr = PolarAxes.PolarTransform()
    ix = ['MIEDO\nEXTREMO', 'MIEDO', 'NEUTRO', 'AVARICIA', 'AVARICIA\nEXTREMA']

    pi = np.pi
    angle_ticks = [(0.00, r"$0$"),
                   (0.20 * pi, r"$\frac{1}{5}\pi$"),
                   (0.40 * pi, r"$\frac{2}{5}\pi$"),
                   (0.60 * pi, r"$\frac{3}{5}\pi$"),
                   (0.80 * pi, r"$\frac{4}{5}\pi$")]

    grid_loc01 = FixedLocator([v for v, s in angle_ticks])
    tick_for01 = DictFormatter(dict(angle_ticks))

    grid_loc02 = MaxNLocator(1)
    grid_help01 = floating_axes.GridHelperCurveLinear(tr, extremes=(pi, 0.00, 2, 1),
                                                          grid_locator1=grid_loc01,   grid_locator2=grid_loc02,
                                                          tick_formatter1=tick_for01, tick_formatter2=None)

    fg.suptitle('CNN Fear and Greed Index', color='cyan', fontsize='medium')
    ax = fg.add_subplot(121, axes_class=floating_axes.FloatingAxes, grid_helper=grid_help01)
    ay = fg.add_subplot(122, axes_class=floating_axes.FloatingAxes, grid_helper=grid_help01)
    ax.grid()
    ay.grid()

    (fear, vix) = fear_vix()
    (xf, yf, color) = xy_color(fear)
    char_plot(ax=ax, x=xf, y=yf, score=fear, color=color, titulo='Feeling')

    (xv, yv, color) = xy_color(vix)
    char_plot(ax=ay, x=xv, y=yv, score=vix, color=color, titulo='Volatility')

    cv.draw()

    return


if __name__ == '__main__':
    win = tk.Tk()
    dimension = "%dx%d+0+0" % (600, 400)
    win.geometry(dimension)
    win.config(bg="black")

    win1 = tk.Frame(win, bg='black', bd=2)
    win1.grid(row=0, column=0, padx=1, pady=5)

    global fg, cv
    gcolor = 'black'
    fg = Figure(figsize=(5.0, 5.0), dpi=110, layout="tight")
    fg.set_facecolor(gcolor)
    cv = FigureCanvasTkAgg(fg, master=win1)
    cv.draw()
    cv.get_tk_widget().pack()

    setup_axes()
    mainloop()
