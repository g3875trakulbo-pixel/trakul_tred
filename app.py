import streamlit as st
import pandas as pd
import re
from io import BytesIO

# --- 1. ตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบครูตระกูล v9.9.5", layout="wide")

def normalize_name(text):
    """ฟอกชื่อให้สะอาดเพื่อใช้ Match: ตัดช่องว่างและคำนำหน้า"""
    if not text or pd.isna(text): return ""
    t = str(text).replace(" ", "").replace("\xa0", "")
    t = re.sub(r'(เด็กชาย|เด็กหญิง|นาย|นางสาว|ด\.ช\.|ด\.ญ\.|น\.ส\.|นาง|ชื่อ|นามสกุล|:|：)', '', t)
    return t

# --- 2. ฟังก์ชันประมวลผล (Core Logic) ---

def process_final_sync(m_files, p_files):
    # 1. สร้างฐานข้อมูลจากไฟล์รายชื่อฝ่ายทะเบียน (Master)
    master_db = []
    for f in m_files:
        try:
            df = pd.read_excel(f) if f.name.endswith(('.xlsx', '.xls')) else pd.read_csv(f, encoding='utf-8-sig')
            c_sid = next((c for c in df.columns if "เลขที่" in str(c)), None)
            c_name = next((c for c in df.columns if any(k in str(c) for k in ["ชื่อ", "นามสกุล"])), None)
            
            if c_name:
                room_label = f.name.split('.')[0]
                room_id = "".join(re.findall(r'\d+', room_label)) # รหัสห้องจริง
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

    # 3. เตรียมคอลัมน์กิจกรรม 1.1 - 1.14
    acts = [f"1.{i}" for i in range(1, 15)]
    for a in acts: df_final[a] = 0

    # 4. 🔥 การอ้างอิงกลับ (Reference Matching): ตรวจสอบความถูกต้องรายคน
    for work in padlet_works:
        for idx, student in df_final.iterrows():
            if student['name_key'] != "" and student['name_key'] in work['content_key']:
                # ตรวจสอบว่าเลขที่หรือห้องที่พิมพ์มา ตรงกับไฟล์ทะเบียนไหม
                is_wrong = False
                if work['sid_typed'] and work['sid_typed'] != student['เลขที่_จริง']: is_wrong = True
                if work['room_typed'] and student['room_id_จริง'] not in work['room_typed']: is_wrong = True
                
                # บันทึกสถานะ (1=ตรง, 2=ข้อมูลแฝงผิดแต่ชื่อตรง)
                current = df_final.at[idx, work['act']]
                if is_wrong:
                    if current == 0: df_final.at[idx, work['act']] = 2
                else:
                    df_final.at[idx, work['act']] = 1
                    
    return df_final, acts

# --- 3. ส่วนแสดงผล ---

def main():
    st.markdown("### 📋 ระบบครูตระกูล v9.9.5 (Final Master Sync)")
    st.write("อ้างอิงเลขที่และห้องจากไฟล์ทะเบียนโรงเรียนเป็นหลัก")

    col1, col2 = st.columns(2)
    m_files = col1.file_uploader("📂 1. อัปโหลดรายชื่อฝ่ายทะเบียน (Master)", accept_multiple_files=True)
    p_files = col2.file_uploader("📂 2. อัปโหลดไฟล์งานจาก Padlet", accept_multiple_files=True)

    if m_files and p_files:
        df_res, acts = process_final_sync(m_files, p_files)
        
        for room in sorted(df_res['ห้อง_จริง'].unique()):
            st.info(f"🏫 บัญชีรายชื่อห้อง: {room}")
            room_df = df_res[df_res['ห้อง_จริง'] == room].copy()
            room_df['สรุปส่ง'] = room_df[acts].apply(lambda x: (x > 0).sum(), axis=1)
            
            # แปลงรหัสเป็นสัญลักษณ์
            display_df = room_df.copy()
            for a in acts:
                display_df[a] = display_df[a].map({1: "✅", 2: "⚠️", 0: "-"})
            
            st.dataframe(
                display_df[['เลขที่_จริง', 'ชื่อ_ทะเบียน'] + acts + ['สรุปส่ง']]
                .rename(columns={'เลขที่_จริง': 'เลขที่', 'ชื่อ_ทะเบียน': 'ชื่อ-นามสกุล'}),
                use_container_width=True, hide_index=True
            )
            
            # ปุ่ม Export
            buf = BytesIO()
            room_df.to_excel(buf, index=False)
            st.download_button(f"📥 โหลด Excel {room}", buf.getvalue(), f"Official_Report_{room}.xlsx")
    else:
        st.info("กรุณาอัปโหลดไฟล์รายชื่อและไฟล์งานเพื่อเริ่มกระบวนการตรวจสอบ")

if __name__ == "__main__":
    main()
