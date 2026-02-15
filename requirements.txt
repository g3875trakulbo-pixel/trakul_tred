import streamlit as st
import pandas as pd
import ccxt 
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1] ตั้งค่าหน้าจอแบบ Wide และปิด Sidebar เริ่มต้น ---
st.set_page_config(page_title="Rule 10 Predictor Pro", layout="wide")

# --- [2] ส่วนหัวแอป (Header) ---
st.markdown("""
    <div style="background-color: #1a1a1a; padding: 20px; border-radius: 10px; border-bottom: 3px solid #FFD700; margin-bottom: 25px;">
        <h1 style='text-align: center; color: #FFD700;'>🕯️ Candlestick Predictor Pro (Rule 10)</h1>
        <p style='text-align: center; color: #888;'>ระบบวิเคราะห์ Real-time และทำนายแท่งเทียนล่วงหน้าสำหรับอาจารย์เจมส์</p>
    </div>
""", unsafe_allow_html=True)

# --- [3] ตัวเลือกเหรียญ 5 เหรียญ (Full Width) ---
coin_list = ["BONK/USDT", "DOGE/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT"]
if 'symbol' not in st.session_state:
    st.session_state.symbol = "BTC/USDT"

cols = st.columns(5)
for i, coin in enumerate(coin_list):
    if cols[i].button(coin, use_container_width=True):
        st.session_state.symbol = coin

symbol = st.session_state.symbol

# --- [4] ดึงข้อมูลจาก Binance API ---
try:
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # แสดงกราฟราคาปัจจุบัน (เต็มความกว้าง)
    st.subheader(f"📊 กราฟราคา Real-time: {symbol}")
    fig_market = go.Figure(data=[go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close']
    )])
    fig_market.update_layout(height=450, template="plotly_dark", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig_market, use_container_width=True)

    # --- [5] การคำนวณกฎ 10 ข้อ (Logic Scoring) ---
    df['RSI'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'])
    df = pd.concat([df, macd], axis=1)
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # คำนวณคะแนน (ตัวอย่างตรรกะ Rule 10)
    score = 0
    if last['close'] > last['open']: score += 1      # 1. แท่งปัจจุบันสีเขียว
    if last['close'] > prev['close']: score += 1    # 2. ปิดสูงกว่าแท่งก่อน
    if last['volume'] > df['volume'].mean(): score += 1 # 3. Volume มากกว่าค่าเฉลี่ย
    if last['RSI'] < 45: score += 2                 # 6. RSI อยู่ในโซนล่าง (มีแรงดีด)
    if last['MACD_12_26_9'] > last['MACDs_12_26_9']: score += 2 # 7. MACD ตัดขึ้น
    # (อาจารย์เพิ่มกฎข้อ 4, 5, 8, 9, 10 ตามเงื่อนไขที่ต้องการได้เลยครับ)

    # --- [6] กราฟทำนายล่วงหน้า 1 แท่ง (Future Prediction) ---
    st.divider()
    st.subheader("🔮 กราฟทำนายทิศทางแท่งถัดไป")
    
    next_time = last['timestamp'] + timedelta(hours=1)
    
    # ถ้าคะแนนรวม >= 4 ให้ทายว่า "ขึ้น"
    if score >= 4:
        p_open = last['close']
        p_close = p_open * 1.012  # สมมติกำไร 1.2%
        verdict, v_color = "ขึ้น (BULLISH)", "#00FF00"
    else:
        p_open = last['close']
        p_close = p_open * 0.988  # สมมติขาดทุน 1.2%
        verdict, v_color = "ลง (BEARISH)", "#FF4B4B"

    # สร้างกราฟเปรียบเทียบ (ข้อมูลเดิม + แท่งทำนาย)
    fig_predict = go.Figure(data=[
        go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="ข้อมูลจริง"),
        go.Candlestick(
            x=[next_time], open=[p_open], high=[max(p_open, p_close)*1.005], 
            low=[min(p_open, p_close)*0.995], close=[p_close], 
            name="ทำนายแท่งถัดไป", increasing_line_color='#00FFFF', decreasing_line_color='#FF00FF'
        )
    ])
    fig_predict.update_layout(height=500, template="plotly_dark")
    st.plotly_chart(fig_predict, use_container_width=True)

    # --- [7] แถบสรุปคำทำนายและราคา ---
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 30px; border-radius: 15px; border: 2px solid {v_color}; text-align: center;">
            <h1 style='color: {v_color};'>ผลวิเคราะห์: {verdict}</h1>
            <div style="display: flex; justify-content: center; gap: 30px;">
                <div style="background-color: #0d4d10; padding: 20px; border-radius: 10px; width: 40%;">
                    <h3 style="color: white;">🟢 จุดควรซื้อ (Entry)</h3>
                    <h2 style="color: #00FF00;">{p_open * 0.997:.8f}</h2>
                </div>
                <div style="background-color: #4d0d0d; padding: 20px; border-radius: 10px; width: 40%;">
                    <h3 style="color: white;">🔴 จุดควรขาย (Exit)</h3>
                    <h2 style="color: #FF4B4B;">{p_close * 1.003:.8f}</h2>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- [8] ตารางกฎ 10 ข้อ (ล่างสุด) ---
    st.divider()
    st.markdown("""
        <div style="background-color: #121212; padding: 25px; border-radius: 10px; border: 1px solid #333;">
            <h3 style="color: #FFD700; text-align: center; margin-bottom: 20px;">📚 กฎ 10 ข้อแห่งความแม่นยำ (Checklist)</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; color: #eee; font-size: 14px;">
                <div>1. Price Action | 2. Color Sequence | 3. Volume Flow | 4. Support/Resistance | 5. Trend Alignment</div>
                <div>6. RSI Momentum | 7. MACD Cross | 8. Volatility | 9. Rejection Wick | 10. Pattern Confirmation</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ ไม่สามารถดึงข้อมูลได้: {e}")
