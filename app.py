import streamlit as st
import pandas as pd
import ccxt 
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1] การตั้งค่าหน้าจอแบบ Wide ---
st.set_page_config(page_title="แอปพยากรณ์แท่งเทียน", layout="wide")

# --- [2] ส่วน Header (รูปโปรไฟล์ และ ชื่อแอปภาษาไทย) ---
# หมายเหตุ: อาจารย์สามารถเปลี่ยนลิงก์รูปภาพใน src เป็นลิงก์รูปจริงของอาจารย์ได้ครับ
st.markdown("""
    <div style="display: flex; align-items: center; background-color: #1a1a1a; padding: 10px; border-radius: 15px; border-bottom: 2px solid #FFD700; margin-bottom: 20px;">
        <img src="https://via.placeholder.com/80" style="border-radius: 50%; width: 60px; height: 60px; border: 2px solid #FFD700; margin-right: 15px;">
        <div>
            <h2 style='color: #FFD700; margin: 0;'>แอปทำนาย Predictor Pro (Rule 10)</h2>
            <p style='color: #888; margin: 0; font-size: 14px;'>ตระกูลบุญชิต | วิเคราะห์เทคนิคอล Real-time</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- [3] แถบเลือกเหรียญ ---
coin_list = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "BONK/USDT"]
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = "BTC/USDT"

cols = st.columns(5)
for i, coin in enumerate(coin_list):
    if cols[i].button(coin, use_container_width=True):
        st.session_state.selected_symbol = coin

symbol = st.session_state
