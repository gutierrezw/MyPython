import os
import io
import ta
import re
import sys
import csv
import ast
import math
import xml.etree.ElementTree as ET

import copy
import signal
import joblib
import urllib
import urllib3
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import hashlib
import textwrap
import webbrowser
import random
import shutil
import string
import ntplib
import psutil
import asyncio
import calendar
import requests
import websocket
import functools
import subprocess
import warnings
import traceback
import pyautogui

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


from decimal import Decimal, InvalidOperation
import pdfplumber
from operator import itemgetter
from pathlib import Path
from zipfile import ZipFile
import pymysql
from pymysql import connect, Error
from dbutils.pooled_db import PooledDB
from dateutil import parser
from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor
from pandas.errors import EmptyDataError
from tkinter import filedialog, scrolledtext, mainloop, filedialog
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    CallbackQueryHandler,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

import mpl_toolkits.axisartist.floating_axes as floating_axes

from cryptography.hazmat.primitives import serialization

from pprint import *
from typing import Dict, List, Union, Optional, Tuple

from requests.exceptions import HTTPError
from cachetools import cached, TTLCache

from functools import wraps

from tkinter import ttk, messagebox, VERTICAL, HORIZONTAL, N, S, E, W
from datetime import datetime, date, timedelta, timezone
from base64 import b64encode
from dateutil.relativedelta import relativedelta
from fake_useragent import UserAgent
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD

from PIL import Image, ImageTk
from matplotlib import ticker, colormaps
from matplotlib.figure import Figure
from matplotlib import pyplot as plt
from matplotlib import dates as mdates
from matplotlib import patches as mpatches
from matplotlib.projections import PolarAxes
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.axisartist.grid_finder import DictFormatter, FixedLocator, MaxNLocator
from matplotlib.dates import (
    AutoDateLocator,
    ConciseDateFormatter,
    DateFormatter,
    MonthLocator,
)
from finvizfinance.group.performance import Performance

import anthropic
import feedparser

# modulos IA
from sklearn.exceptions import UndefinedMetricWarning
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, f1_score, roc_auc_score
