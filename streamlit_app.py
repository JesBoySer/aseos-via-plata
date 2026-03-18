import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import requests
import base64
from io import StringIO
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="SCA - IES Vía de la Plata",
    layout="wide",
    page_icon="🚾"
)

st_autorefresh(interval=30000, key="refresh")

MAX_MINUTOS = 10

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = st.secrets["GITHUB_FILE"]

st.markdown("""
<style>

.stApp{
background:#0B1120;
color:#E2E8F0;
}

/* === SELECTBOX / MULTISELECT: fondo negro y texto blanco === */

/* Caja del control (cerrado) */
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
  background: #000000 !important;     /* negro */
  color: #ffffff !import
