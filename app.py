import streamlit as st
import pandas as pd
import ccxt 
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="แอปพยากรณ์แท่งเทียน", layout="wide")

# --- ส่วน Header ชื่อแอปและชื่อเจ้าของ (ตระกูลบุญชิต) ---
st.markdown("""
    <div style="display: flex; align-items: center; background-color: #1a1a1a; padding: 15px; border-radius: 15px; border-bottom: 2px solid #FFD700; margin-bottom: 25px;">
        <div style="background-color: #FFD700; border-radius: 50%; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; margin-right: 15px;">
            <span style="font-size: 20px;">👤</span>
        </div>
        <div>
            <h2 style='color: #FFD700; margin: 0;'>แอปทำนาย Predictor Pro (Rule 10)</h2>
            <p style='color: #888; margin: 0; font-size: 14px;'>โดย: ตระกูลบุญชิต | วิเคราะห์เทคนิคอล Real-time</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- ปุ่มเลือกเหรียญ ---
coin_list = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "BONK/USDT"]
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = "BTC/USDT"

cols = st.columns(5)
for i, coin in enumerate(coin_list):
    if cols[i].button(coin, use_container_width=True):
        st.session_state.selected_symbol = coin

symbol = st.session_state.selected_symbol

# --- ฟังก์ชันดึงข้อมูลแบบป้องกันการโดนบล็อก ---
@st.cache_data(ttl=30)
def get_crypto_data(symbol):
    # ลองดึงจาก Binance ก่อน ถ้าไม่ได้ให้สลับไป KuCoin หรือ Kraken อัตโนมัติ
    exchanges = [
        ccxt.binance({'enableRateLimit': True}),
        ccxt.kucoin({'enableRateLimit': True}),
        ccxt.kraken({'enableRateLimit': True})
    ]
    for ex in exchanges:
        try:
            ohlcv = ex.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except:
            continue
    return None

try:
    df = get_crypto_data(symbol)
    
    if df is not None:
        # กราฟปัจจุบัน
        st.markdown(f"### 📊 ตลาดสด: {symbol}")
        fig_market = go.Figure(data=[go.Candlestick(
            x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close']
        )])
        fig_market.update_layout(height=400, template="plotly_dark", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_market, use_container_width=True)

        # วิเคราะห์ Rule 10
        df['RSI'] = ta.rsi(df['close'], length=14)
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        last = df.iloc[-1]
        
        score = 0
        if last['close'] > last['open']: score += 1
        if last['RSI'] < 45: score += 2
        if last['MACD_12_26_9'] > last['MACDs_12_26_9']: score += 2

        # พยากรณ์
        st.divider()
        next_time = last['timestamp'] + timedelta(hours=1)
        if score >= 3:
            p_open, p_close = last['close'], last['close'] * 1.01
            verdict, v_color = "ขึ้น (BULLISH)", "#00FF00"
        else:
            p_open, p_close = last['close'], last['close'] * 0.99
            verdict, v_color = "ลง (BEARISH)", "#FF4B4B"

        fig_predict = go.Figure(data=[
            go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="จริง"),
            go.Candlestick(x=[next_time], open=[p_open], high=[max(p_open,p_close)*1.002], low=[min(p_open,p_close)*0.998], close=[p_close], 
                           name="ทำนาย", increasing_line_color='cyan', decreasing_line_color='orange')
        ])
        fig_predict.update_layout(height=450, template="plotly_dark")
        st.plotly_chart(fig_predict, use_container_width=True)

        # แถบผลลัพธ์
        st.markdown(f"""
            <div style="background-color: #1a1a1a; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid {v_color};">
                <h2 style='color:{v_color}; margin:0;'>ทำนาย: {verdict}</h2>
                <div style="display: flex; justify-content: center; gap: 20px; margin-top:15px;">
                    <div style="background-color: #28a745; color: white; padding: 10px 30px; border-radius: 15px; font-weight: bold;">เข้าซื้อ: {p_open:.4f}</div>
                    <div style="background-color: #dc3545; color: white; padding: 10px 30px; border-radius: 15px; font-weight: bold;">ขาย: {p_close:.4f}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.error("❌ ไม่สามารถดึงข้อมูลได้ โปรดรอสักครู่หรือลองสลับเหรียญเพื่อรีเฟรช")

except Exception as e:
    st.error(f"เกิดข้อผิดพลาด: {e}")
