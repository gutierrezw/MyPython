# libs.py

import os
import os.path
import sys

# import mysql.connector
from pathlib import Path
from datetime import datetime, date, timedelta, time as dtime
from tkinter import ttk, messagebox, VERTICAL, HORIZONTAL, N, S, E, W

from pymysql import connect, Error
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
