import os
import io
import ta
import re
import sys
import csv
import ast
import math
import xml.etree.ElementTree as ET

import hmac
import copy
import signal
import joblib
import urllib
import urllib3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import hashlib
import textwrap
import random
import string
import psutil
import syncio
import asyncio
import calendar
import shutil
from decimal import Decimal, InvalidOperation
import requests
import websocket
import functools
import subprocess
import warnings
import traceback
import pyautogui
import multiprocessing

import ssl as ssl
import sys as sys
import numpy as np
import json as json
import time as time
import pandas as pd
import logging as logging
import tkinter as tk
import yfinance as yf

# import requests_cache
import webbrowser as webbrowser
import mplfinance as mpf
import fnmatch as fnmatch
import openpyxl as openpyxl
import schedule as schedule
import threading as threading


from diskcache import Cache
from operator import itemgetter
from pathlib import Path
from zipfile import ZipFile
from pymysql import connect, Error
import pdfplumber
from sqlalchemy import create_engine
from dateutil import parser
from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor
from pandas.errors import EmptyDataError
from tkinter import filedialog, scrolledtext, mainloop, filedialog
from yfinance.exceptions import YFRateLimitError
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    Updater,
    CallbackQueryHandler,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

import mpl_toolkits.axisartist.angle_helper as angle_helper
import mpl_toolkits.axisartist.floating_axes as floating_axes

from cryptography.hazmat.primitives import serialization

from pprint import *
from typing import Dict, List, Union, Optional, Tuple
from multiprocessing import Process

from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from cachetools import cached, TTLCache
from diskcache import Cache

from urllib3.util.retry import Retry
from functools import wraps

from tkinter import ttk, messagebox, VERTICAL, HORIZONTAL, N, S, E, W
from datetime import datetime, date, timedelta, timezone, time as dtime
from base64 import urlsafe_b64decode, urlsafe_b64encode, b64encode, b64decode
from dateutil.relativedelta import relativedelta
from fake_useragent import UserAgent
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, EMAIndicator, MACD

from PIL import Image, ImageTk, ImageColor, ImageDraw
from matplotlib import ticker, colormaps
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
from matplotlib.gridspec import GridSpec
from matplotlib import patches as mpatches
from matplotlib.projections import PolarAxes
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.axisartist.grid_finder import DictFormatter, FixedLocator, MaxNLocator
from matplotlib.dates import (
    FR,
    MO,
    MONTHLY,
    SA,
    SU,
    TH,
    TU,
    WE,
    AutoDateFormatter,
    AutoDateLocator,
    ConciseDateFormatter,
    DateFormatter,
    DayLocator,
    HourLocator,
    MicrosecondLocator,
    MinuteLocator,
    MonthLocator,
    RRuleLocator,
    SecondLocator,
    WeekdayLocator,
    YearLocator,
    rrulewrapper,
)
from finvizfinance.quote import finvizfinance
from finvizfinance.group.overview import Overview
from finvizfinance.group.performance import Performance

# modulos IA
from sklearn.exceptions import UndefinedMetricWarning
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, f1_score, roc_auc_score
