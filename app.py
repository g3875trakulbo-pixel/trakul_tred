import streamlit as st
import pandas as pd
import re, os
from io import BytesIO

# --- 1. การตั้งค่าหน้าจอ ---
st.set_page_config(page_title="ระบบครูตระกูล v9.8.3", layout="wide")

# --- 2. ฟังก์ชันประมวลผล (จุดที่แก้ไขเรื่องชื่อซ้ำ) ---

def process_master_files(files):
    levels_db = {}
    for f in files:
        name = f.name.replace('.xlsx', '').replace('.csv', '')
        level_match = re.search(r'(ม\.\d+)', name)
        level = level_match.group(1) if level_match else "ระดับอื่นๆ"
        
        df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
        c_sid = next((c for c in df.columns if "เลขที่" in str(c)), None)
        c_name = next((c for c in df.columns if any(k in str(c) for k in ["ชื่อ", "นามสกุล"])), None)
        
        if c_sid and c_name:
            df_clean = df[[c_sid, c_name]].copy()
            df_clean[c_sid] = pd.to_numeric(df_clean[c_sid], errors='coerce')
            df_clean = df_clean.dropna(subset=[c_sid])
            df_clean[c_sid] = df_clean[c_sid].astype(int)
            df_clean.columns = ['เลขที่', 'ชื่อ - นามสกุล']
            
            # ✅ ลบรายชื่อซ้ำในไฟล์ต้นฉบับ
            df_clean = df_clean.drop_duplicates(subset=['เลขที่'], keep='first')
            
            if level not in levels_db: levels_db[level] = {}
            levels_db[level][name] = df_clean
    return levels_db

def process_padlet_files(files):
    all_data = []
    for f in files:
        df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
        # หาคอลัมน์ห้อง
        col_sec = next((c for c in df.columns if any(k in str(c).lower() for k in ["ส่วน", "section", "ห้อง"])), None)
        
        for _, row in df.iterrows():
            content_str = " ".join(map(str, row.values))
            sid_match = re.search(r'(?:เลขที่|No\.|#|n)\s*(\d+)', content_str, re.I)
            act_match = re.search(r'1\.(\d{1,2})', content_str)
            
            if sid_match and act_match:
                # ดึงเลขห้องออกมาเป็นตัวเลขล้วน (เช่น "ม.3/1" -> "31") เพื่อใช้เช็คเบื้องต้น
                raw_room = str(row[col_sec]) if col_sec else ""
                room_digits = "".join(re.findall(r'\d+', raw_room))
                
                all_data.append({
                    'เลขที่': int(sid_match.group(1)),
                    'กิจกรรม': f"1.{act_match.group(1)}",
                    'รหัสห้อง': room_digits  # ใช้แค่ตัวเลขเพื่อความแม่นยำในการ Group
                })
    
    if not all_data: return pd.DataFrame()
    
    df_raw = pd.DataFrame(all_data)
    
    # ✅ แก้ไขจุดนี้: ยุบรวมข้อมูลโดยไม่สนว่าเด็กจะพิมพ์ห้องมาต่างกันกี่แบบ
    # ถ้าเลขที่เดียวกัน กิจกรรมเดียวกัน อยู่ในรหัสห้องเดียวกัน ให้ยุบเหลือบรรทัดเดียว
    pivot = df_raw.pivot_table(
        index=['เลขที่', 'รหัสห้อง'],
        columns='กิจกรรม',
        aggfunc='max', 
        fill_value=0
    ).reset_index()
    
    return pivot

# --- 3. ส่วนแสดงผล ---

def main():
    st.title("📋 ระบบเช็คงานครูตระกูล v9.8.3 (Zero Duplicate)")
    
    m_files = st.sidebar.file_uploader("📂 1. อัปโหลดรายชื่อ", accept_multiple_files=True)
    p_files = st.sidebar.file_uploader("📂 2. อัปโหลด Padlet", accept_multiple_files=True)

    if m_files and p_files:
        levels_db = process_master_files(m_files)
        pivot_padlet = process_padlet_files(p_files)
        
        full_acts = [f"1.{i}" for i in range(1, 15)]

        for level in sorted(levels_db.keys()):
            st.header(f"ระดับชั้น {level}")
            
            for room_name, df_student in levels_db[level].items():
                # สกัดเลขห้องจากชื่อไฟล์รายชื่อ (เช่น "ม.3-1" -> "31")
                target_room = "".join(re.findall(r'\d+', room_name))
                
                # กรองงานจาก Padlet เฉพาะห้องนี้
                df_work = pivot_padlet[pivot_padlet['รหัสห้อง'] == target_room].copy()
                
                # ✅ รวมข้อมูล: รายชื่อนักเรียน (ตั้งต้น) + งานที่ส่ง
                # join ด้วย 'เลขที่' อย่างเดียว ชื่อจะไม่มีทางซ้ำ
                final_df = df_student.merge(df_work.drop(columns=['รหัสห้อง'], errors='ignore'), 
                                          on='เลขที่', how='left').fillna(0)
                
                # ล้างซ้ำรอบสุดท้ายเพื่อความชัวร์
                final_df = final_df.drop_duplicates(subset=['เลขที่'])
                
                for a in full_acts:
                    if a not in final_df.columns: final_df[a] = 0
                
                final_df['รวม'] = final_df[full_acts].sum(axis=1)
                
                st.subheader(f"🏫 ห้อง {room_name}")
                st.dataframe(final_df[['เลขที่', 'ชื่อ - นามสกุล'] + full_acts + ['รวม']], use_container_width=True, hide_index=True)
                
                # ปุ่มโหลด
                csv = final_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(f"📥 โหลดไฟล์ {room_name}", csv, f"{room_name}.csv", "text/csv")

if __name__ == "__main__":
    main()
