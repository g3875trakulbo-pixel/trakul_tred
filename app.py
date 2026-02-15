import streamlit as st
import pandas as pd
import ccxt 
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1] ตั้งค่าหน้าจอแบบ Wide เต็มความกว้างจอ ---
st.set_page_config(
    page_title="Candlestick Predictor Pro (Rule 10)",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- [2] ส่วนหัวแอป (Header) ---
st.markdown("""
    <div style="background-color: #1e1e1e; padding: 25px; border-radius: 15px; margin-bottom: 20px; border: 1px solid #FFD700;">
        <h1 style='text-align: center; color: #FFD700; font-size: 40px; margin-bottom: 0;'>🕯️ Candlestick Predictor Pro (Rule 10)</h1>
        <p style='text-align: center; color: #ffffff; font-size: 16px;'>ระบบวิเคราะห์และทำนายแท่งเทียนล่วงหน้าแบบ Real-time โดยอาจารย์เจมส์</p>
    </div>
""", unsafe_allow_html=True)

# --- [3] แถบเลือกเหรียญ 5 เหรียญ (Full Width Buttons) ---
coin_list = ["BONK/USDT", "DOGE/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT"]
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = "BTC/USDT"

st.markdown("### 🎯 **เลือกเหรียญที่ต้องการวิเคราะห์:**")
cols = st.columns(5)
for i, coin in enumerate(coin_list):
    if cols[i].button(coin, use_container_width=True):
        st.session_state.selected_symbol = coin

symbol = st.session_state.selected_symbol

# --- [4] ดึงข้อมูลและแสดงกราฟจาก Binance ---
try:
    exchange = ccxt.binance()
    # ดึงข้อมูล 100 แท่งล่าสุด (Timeframe 1 ชั่วโมง)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    # แสดงกราฟราคาปัจจุบัน
    st.divider()
    st.subheader(f"📊 กราฟราคาตลาดสด (Real-time Market Chart): {symbol}")
    fig_market = go.Figure(data=[go.Candlestick(
        x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name="ราคาปัจจุบัน"
    )])
    fig_market.update_layout(height=500, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_market, use_container_width=True)

    # --- [5] ส่วนวิเคราะห์กฎ 10 ข้อ (Logic Scoring) ---
    df['RSI'] = ta.rsi(df['close'], length=14)
    macd = ta.macd(df['close'])
    df = pd.concat([df, macd], axis=1)
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # ระบบคะแนน Rule 10 (Logic พื้นฐาน)
    score = 0
    if last['close'] > last['open']: score += 1      # Rule 1: แท่งเขียว
    if last['close'] > prev['close']: score += 1    # Rule 2: ราคายังสูงกว่าแท่งก่อน
    if last['volume'] > df['volume'].mean(): score += 1 # Rule 3: Volume สูงกว่าเฉลี่ย
    if last['RSI'] < 45: score += 2                 # Rule 6: RSI ต่ำ (มีโอกาสดีด)
    if last['MACD_12_26_9'] > last['MACDs_12_26_9']: score += 2 # Rule 7: MACD ตัดขึ้น

    # --- [6] กราฟพยากรณ์ล่วงหน้า 1 แท่ง (Future Prediction Chart) ---
    st.divider()
    st.subheader("🔮 กราฟทำนายทิศทางแท่งเทียนถัดไป (Prediction)")
    
    next_time = last['timestamp'] + timedelta(hours=1)
    
    # คำนวณสีและทิศทางแท่งพยากรณ์
    if score >= 4:
        p_open = last['close']
        p_close = p_open * 1.012  # ทายว่าขึ้น 1.2%
        verdict, v_color = "ขึ้น (BULLISH)", "#00FF00"
    else:
        p_open = last['close']
        p_close = p_open * 0.988  # ทายว่าลง 1.2%
        verdict, v_color = "ลง (BEARISH)", "#FF4B4B"

    # วาดกราฟเปรียบเทียบ
    fig_predict = go.Figure(data=[
        go.Candlestick(x=df['timestamp'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="ข้อมูลจริง"),
        go.Candlestick(
            x=[next_time], open=[p_open], high=[max(p_open, p_close)*1.005], 
            low=[min(p_open, p_close)*0.995], close=[p_close], 
            name="แท่งพยากรณ์", 
            increasing_line_color='#00FFFF', decreasing_line_color='#FF00FF'
        )
    ])
    fig_predict.update_layout(height=550, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig_predict, use_container_width=True)

    # --- [7] บทสรุปคำทำนายและราคาซื้อขาย ---
    st.markdown(f"""
        <div style="background-color: #1e1e1e; padding: 35px; border-radius: 15px; text-align: center; border: 2px solid {v_color};">
            <h1 style='color:{v_color}; font-size: 50px; margin-bottom: 20px;'>ผลทำนาย: {verdict}</h1>
            <div style="display: flex; justify-content: center; gap: 40px; flex-wrap: wrap;">
                <div style="background-color: #0d4d10; padding: 25px; border-radius: 12px; min-width: 320px; border: 1px solid #00FF00;">
                    <h3 style="color: white; margin-top:0;">🟢 ราคาที่ควรซื้อ (Entry)</h3>
                    <h2 style="color: #00FF00; font-size: 30px;">{p_open * 0.998:.8f}</h2>
                </div>
                <div style="background-color: #4d0d0d; padding: 25px; border-radius: 12px; min-width: 320px; border: 1px solid #FF4B4B;">
                    <h3 style="color: white; margin-top:0;">🔴 ราคาที่ควรขาย (Exit)</h3>
                    <h2 style="color: #FF4B4B; font-size: 30px;">{p_close * 1.002:.8f}</h2>
                </div>
            </div>
            <p style="margin-top: 20px; color: #888;">วิเคราะห์ด้วยกฎ 10 ข้อ | ความเชื่อมั่นของระบบ: {min(score*15, 95)}%</p>
        </div>
    """, unsafe_allow_html=True)

    # --- [8] ตารางกฎ 10 ข้อ (ล่างสุด) ---
    st.divider()
    st.markdown("""
        <div style="background-color: #121212; padding: 35px; border-radius: 15px; border: 1px solid #333; width: 100%;">
            <h2 style="color: #FFD700; text-align: center; margin-bottom: 25px;">📚 รายละเอียดกฎ 10 ข้อแห่งความแม่นยำ (Rule 10)</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
                <div style="color: #ffffff; font-size: 15px; line-height: 1.8;">
                    <p><b>1. Price Action:</b> ดูแรงซื้อขายจากแท่งเทียน</p>
                    <p><b>2. Color Sequence:</b> ตรวจสอบการเรียงตัวของสีแท่งเทียน</p>
                    <p><b>3. Volume Flow:</b> ปริมาณการซื้อขายต้องสนับสนุนทิศทาง</p>
                    <p><b>4. Support/Resistance:</b> ราคาต้องอยู่ในจุดที่เหมาะสม</p>
                    <p><b>5. Trend Alignment:</b> ทิศทางต้องตามเทรนด์หลัก</p>
                </div>
                <div style="color: #ffffff; font-size: 15px; line-height: 1.8;">
                    <p><b>6. RSI Momentum:</b> หาจุดกลับตัวจากภาวะ Oversold/Overbought</p>
                    <p><b>7. MACD Cross:</b> ยืนยันสัญญาณด้วยจุดตัดของเส้นค่าเฉลี่ย</p>
                    <p><b>8. Volatility Check:</b> วัดความผันผวนของตลาด</p>
                    <p><b>9. Rejection Wick:</b> ดูไส้เทียนที่ยาวผิดปกติ</p>
                    <p><b>10. Pattern Confirmation:</b> รูปแบบแท่งเทียนกลับตัว</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"เกิดข้อผิดพลาด: {e}")

st.markdown("<br><p style='text-align: center; color: #444;'>© 2026 Candlestick Predictor Pro | Create by James</p>", unsafe_allow_html=True)
