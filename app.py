import streamlit as st
import pandas as pd
import re
from io import BytesIO

# --- 1. ตั้งค่าหน้าจอ (ขยายพื้นที่ให้กว้างที่สุด) ---
st.set_page_config(page_title="ระบบครูตระกูล v9.9.6", layout="wide")

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        /* ขยายตารางให้เต็มพื้นที่และปรับแต่ง Header */
        .main-header { background: linear-gradient(90deg, #1b5e20, #4caf50); padding: 20px; border-radius: 10px; text-align: center; color: white; margin-bottom: 20px; }
        .stDataFrame { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

def normalize_name(text):
    if not text or pd.isna(text): return ""
    t = str(text).replace(" ", "").replace("\xa0", "")
    t = re.sub(r'(เด็กชาย|เด็กหญิง|นาย|นางสาว|ด\.ช\.|ด\.ญ\.|น\.ส\.|นาง|ชื่อ|นามสกุล|:|：)', '', t)
    return t.strip()

# --- 2. ฟังก์ชันประมวลผลข้อมูล ---

def process_final_sync(m_files, p_files):
    # 1. สร้างฐานข้อมูลจากไฟล์ทะเบียน (Master)
    master_db = []
    for f in m_files:
        try:
            df = pd.read_excel(f) if f.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f, encoding='utf-8-sig')
            c_sid = next((c for c in df.columns if "เลขที่" in str(c)), None)
            c_name = next((c for c in df.columns if any(k in str(c) for k in ["ชื่อ", "นามสกุล"])), None)
            
            if c_name:
                room_label = f.name.split('.')[0]
                room_id = "".join(re.findall(r'\d+', room_label))
                for _, row in df.iterrows():
                    master_db.append({
                        'name_key': normalize_name(row[c_name]),
                        'เลขที่_จริง': str(int(row[c_sid])) if c_sid and not pd.isna(row[c_sid]) else "-",
                        'ชื่อ_ทะเบียน': str(row[c_name]).strip(),
                        'ห้อง_จริง': room_label,
                        'room_id_จริง': room_id
                    })
        except: continue
    
    df_final = pd.DataFrame(master_db).drop_duplicates(subset=['name_key'])

    # 2. รวบรวมงานจาก Padlet
    padlet_works = []
    for f in p_files:
        try:
            df = pd.read_excel(f) if f.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f, encoding='utf-8-sig')
            col_sec = next((c for c in df.columns if any(k in str(c).lower() for k in ["ส่วน", "ห้อง"])), None)
            for _, row in df.iterrows():
                content = " ".join(map(str, row.values))
                act_match = re.search(r'1\.(\d{1,2})', content)
                sid_match = re.search(r'(?:เลขที่|No\.|#|n)\s*(\d+)', content, re.I)
                if act_match:
                    raw_room = str(row[col_sec]) if col_sec else ""
                    padlet_works.append({
                        'content_key': normalize_name(content),
                        'act': f"1.{act_match.group(1)}",
                        'sid_typed': sid_match.group(1) if sid_match else None,
                        'room_typed': "".join(re.findall(r'\d+', raw_room))
                    })
        except: continue

    # 3. เตรียมคอลัมน์กิจกรรม
    acts = [f"1.{i}" for i in range(1, 15)]
    for a in acts: df_final[a] = 0

    # 4. Matching & Referencing
    for work in padlet_works:
        for idx, student in df_final.iterrows():
            if student['name_key'] != "" and student['name_key'] in work['content_key']:
                is_wrong = False
                if work['sid_typed'] and work['sid_typed'] != student['เลขที่_จริง']: is_wrong = True
                if work['room_typed'] and student['room_id_จริง'] not in work['room_typed']: is_wrong = True
                
                current = df_final.at[idx, work['act']]
                if is_wrong:
                    if current == 0: df_final.at[idx, work['act']] = 2
                else:
                    df_final.at[idx, work['act']] = 1
                    
    return df_final, acts

# --- 3. ส่วนแสดงผล ---

def main():
    inject_custom_css()
    st.markdown('<div class="main-header"><h3>📋 ระบบสรุปผลการส่งงานครูตระกูล v9.9.6</h3></div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("📂 อัปโหลดไฟล์")
        m_files = st.file_uploader("1. รายชื่อฝ่ายทะเบียน (Master)", accept_multiple_files=True)
        p_files = st.file_uploader("2. ไฟล์งานจาก Padlet", accept_multiple_files=True)

    if m_files and p_files:
        df_res, acts = process_final_sync(m_files, p_files)
        
        for room in sorted(df_res['ห้อง_จริง'].unique()):
            st.subheader(f"🏫 ห้อง: {room}")
            room_df = df_res[df_res['ห้อง_จริง'] == room].copy()
            room_df['สรุปส่ง'] = room_df[acts].apply(lambda x: (x > 0).sum(), axis=1)
            
            # แปลงรหัสเป็นสัญลักษณ์
            display_df = room_df.copy()
            for a in acts:
                display_df[a] = display_df[a].map({1: "✅", 2: "⚠️", 0: "-"})
            
            # --- ขยายพื้นที่ตารางสรุป ---
            # กำหนด height ให้สูงพอสำหรับนักเรียนประมาณ 40-50 คนต่อห้อง
            st.dataframe(
                display_df[['เลขที่_จริง', 'ชื่อ_ทะเบียน'] + acts + ['สรุปส่ง']]
                .rename(columns={'เลขที่_จริง': 'เลขที่', 'ชื่อ_ทะเบียน': 'ชื่อ-นามสกุล'}),
                use_container_width=True, 
                hide_index=True,
                height=1200  # ขยายความสูงของพื้นที่ตารางลงไปด้านล่าง
            )
            
            buf = BytesIO()
            room_df.to_excel(buf, index=False)
            st.download_button(f"📥 ดาวน์โหลดไฟล์ Excel ห้อง {room}", buf.getvalue(), f"Report_{room}.xlsx")
    else:
        st.info("💡 คำแนะนำ: ระบบจะยึดชื่อ-นามสกุลจากไฟล์ทะเบียนเป็นหลัก และรวมงานจาก Padlet มาสรุปให้ในบรรทัดเดียวกันครับ")

if __name__ == "__main__":
    main()
