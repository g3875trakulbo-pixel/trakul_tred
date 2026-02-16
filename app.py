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
            <h2 style='color: #FFD700; margin: 0;'>แอปทำนาย Predictor Pro (สูตรลับตระกูลบุญชิต)</h2>
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

        # --- ส่วนการวิเคราะห์ใหม่: กฎ 4 ข้อ (MACD Histogram) ---
        macd = ta.macd(df['close'])
        df = pd.concat([df, macd], axis=1)
        
        # ชื่อคอลัมน์ Histogram ปกติของ pandas_ta คือ MACDh_12_26_9
        hist_col = 'MACDh_12_26_9'
        last_hist = df[hist_col].iloc[-1]
        prev_hist = df[hist_col].iloc[-2]
        
        verdict = ""
        v_color = ""
        rule_name = ""

        # 1. เขียวใส (Histogram > 0 และ สูงขึ้น) -> ขึ้นจริง
        if last_hist > 0 and last_hist > prev_hist:
            rule_name = "เขียวใส (Momentum เพิ่ม)"
            verdict, v_color = "ขึ้นจริง (BULLISH)", "#00FF00"

        # 2. เขียวทึบ (Histogram > 0 แต่ ลดลง) -> ลงจริง
        elif last_hist > 0 and last_hist <= prev_hist:
            rule_name = "เขียวทึบ (Momentum แผ่ว)"
            verdict, v_color = "ลงจริง (BEARISH)", "#006400"

        # 3. แดงใส (Histogram < 0 และ ต่ำลง) -> ลง
        elif last_hist < 0 and last_hist < prev_hist:
            rule_name = "แดงใส (แรงขายเพิ่ม)"
            verdict, v_color = "ลง (BEARISH)", "#FF0000"

        # 4. แดงทึบ (Histogram < 0 แต่ สูงขึ้น) -> ขึ้นจริง
        elif last_hist < 0 and last_hist >= prev_hist:
            rule_name = "แดงทึบ (แรงขายแผ่ว)"
            verdict, v_color = "ขึ้นจริง (BULLISH)", "#8B0000"

        # พยากรณ์ (จำลองราคาเป้าหมาย)
        st.divider()
        last_price = df['close'].iloc[-1]
        next_time = df['timestamp'].iloc[-1] + timedelta(hours=1)
        
        if "ขึ้นจริง" in verdict:
            p_open, p_close = last_price, last_price * 1.01
        else:
            p_open, p_close = last_price, last_price * 0.99

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
                <p style='color: #888; margin:0;'>กฎที่ตรวจพบ: {rule_name}</p>
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
