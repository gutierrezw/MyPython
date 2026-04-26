# libs.py

import datetime
import os
import sys

# import mysql.connector

from pymysql import connect, Error
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
