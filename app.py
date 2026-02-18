import streamlit as st
import pandas as pd
import re
from io import BytesIO

# --- 1. การตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="ระบบครูตระกูล v9.9.0", layout="wide")

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .main-header { background: linear-gradient(90deg, #0d47a1, #1976d2); padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 25px; }
        .room-section { background-color: #f8f9fa; border-left: 8px solid #1565c0; padding: 15px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันหัวใจสำคัญ: การฟอกชื่อ (Name Scrubbing) ---
def normalize_name(text):
    """ทำให้ชื่อสะอาดที่สุดเพื่อใช้ในการจับคู่ (Match)"""
    if not text or pd.isna(text): return ""
    # 1. แปลงเป็นตัวพิมพ์เล็ก (ถ้ามีภาษาอังกฤษ) และลบช่องว่างทั้งหมด
    t = str(text).lower().replace(" ", "").replace("\xa0", "")
    # 2. ลบคำนำหน้าชื่อทุกรูปแบบ
    prefixes = r'(เด็กชาย|เด็กหญิง|นาย|นางสาว|ด\.ช\.|ด\.ญ\.|น\.ส\.|นาง|ชื่อ|นามสกุล|:|：)'
    t = re.sub(prefixes, '', t)
    # 3. ลบอักขระพิเศษและจุด
    t = re.sub(r'[\.\-\_\(\)]', '', t)
    return t

# --- 3. การจัดการข้อมูล Master (รายชื่อที่ถูกต้อง) ---
def process_master_files(files):
    all_students = []
    for f in files:
        try:
            df = pd.read_excel(f) if f.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f, encoding='utf-8-sig')
            # ค้นหาคอลัมน์ เลขที่ และ ชื่อ
            c_sid = next((c for c in df.columns if "เลขที่" in str(c)), None)
            c_name = next((c for c in df.columns if any(k in str(c) for k in ["ชื่อ", "นามสกุล"])), None)
            
            if c_name:
                # ดึงข้อมูลระดับชั้นและห้องจากชื่อไฟล์
                room_info = f.name.replace('.xlsx', '').replace('.csv', '')
                
                for _, row in df.iterrows():
                    raw_name = str(row[c_name])
                    all_students.append({
                        'key': normalize_name(raw_name), # ชื่อที่ฟอกแล้วใช้เป็น Key
                        'display_name': raw_name.strip(),
                        'no': row[c_sid] if c_sid else "-",
                        'room': room_info
                    })
        except: continue
    
    # กำจัดชื่อซ้ำใน Master (ถ้ามีคนชื่อซ้ำกันในรายชื่อห้อง)
    return pd.DataFrame(all_students).drop_duplicates(subset=['key'], keep='first')

# --- 4. การจัดการข้อมูลงาน (Padlet) ---
def process_padlet_works(files):
    works = []
    for f in files:
        try:
            df = pd.read_excel(f) if f.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f, encoding='utf-8-sig')
            for _, row in df.iterrows():
                # รวมข้อมูลทุกช่องในแถวนั้นเป็นข้อความเดียวเพื่อค้นหาชื่อและกิจกรรม
                content = " ".join(map(str, row.values))
                # ค้นหากิจกรรม 1.1 - 1.14
                act_match = re.search(r'1\.(\d{1,2})', content)
                if act_match:
                    works.append({
                        'clean_content': normalize_name(content),
                        'activity': f"1.{act_match.group(1)}"
                    })
        except: continue
    return works

# --- 5. Main Application ---
def main():
    inject_custom_css()
    st.markdown('<div class="main-header"><h1>📋 ระบบเช็คงานครูตระกูล v9.9.0</h1><p>ยึดชื่อ-นามสกุลเป็นฐานข้อมูลหลักเพื่อความแม่นยำสูงสุด</p></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    master_files = col1.file_uploader("📂 1. อัปโหลดรายชื่อนักเรียน (ไฟล์ที่ถูกต้อง)", accept_multiple_files=True)
    padlet_files = col2.file_uploader("📂 2. อัปโหลดไฟล์งานจาก Padlet", accept_multiple_files=True)

    if master_files and padlet_files:
        # ดึงรายชื่อ Master
        df_master = process_master_files(master_files)
        # ดึงงานจาก Padlet
        works = process_padlet_works(padlet_files)
        
        if df_master.empty:
            st.error("ไม่พบคอลัมน์ 'ชื่อ' ในไฟล์รายชื่อ กรุณาตรวจสอบไฟล์ครับ")
            return

        # สร้างตารางกิจกรรม 1.1 - 1.14 รอไว้
        activities = [f"1.{i}" for i in range(1, 15)]
        for act in activities:
            df_master[act] = 0

        # 🚀 อัลกอริทึมการ Match งาน: วนลูปเช็คชื่อนักเรียนในเนื้อหา Padlet
        for work in works:
            # ค้นหาว่า Key ชื่อของนักเรียนคนไหน อยู่ในเนื้อหา Padlet บ้าง
            mask = df_master['key'].apply(lambda k: k in work['clean_content'] if k else False)
            df_master.loc[mask, work['activity']] = 1

        # แสดงผลแยกตามห้อง
        rooms = sorted(df_master['room'].unique())
        for room in rooms:
            with st.container():
                st.markdown(f'<div class="room-section"><h3>🏫 ห้อง: {room}</h3></div>', unsafe_allow_html=True)
                room_data = df_master[df_master['room'] == room].copy()
                room_data['รวม'] = room_data[activities].sum(axis=1)
                
                # แสดงผลตาราง
                display_cols = ['no', 'display_name'] + activities + ['รวม']
                st.dataframe(
                    room_data[display_cols].rename(columns={'no': 'เลขที่', 'display_name': 'ชื่อ-นามสกุล'}),
                    use_container_width=True, hide_index=True
                )
                
                # ปุ่มโหลดรายห้อง
                buf = BytesIO()
                room_data[display_cols].to_excel(buf, index=False)
                st.download_button(f"📥 โหลด Excel {room}", buf.getvalue(), f"Report_{room}.xlsx")
    else:
        st.info("💡 วิธีใช้: อัปโหลดรายชื่อนักเรียนแยกตามห้อง และไฟล์ Padlet ระบบจะจับคู่ชื่อนักเรียนให้เองอัตโนมัติครับ")

if __name__ == "__main__":
    main()
