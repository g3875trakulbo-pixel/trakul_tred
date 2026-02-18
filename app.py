import streamlit as st
import pandas as pd
import re, os, base64
from io import BytesIO

# --- 1. การตั้งค่าหน้าจอและสไตล์ ---
st.set_page_config(page_title="ระบบครูตระกูล v9.8.2", layout="wide", page_icon="📝")

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
        html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }
        .main-header { background: linear-gradient(90deg, #1b5e20, #4caf50); padding: 25px; border-radius: 15px; text-align: center; color: white; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .level-section { background-color: #2e7d32; padding: 10px 20px; border-radius: 8px; color: white; margin: 40px 0 10px 0; font-size: 1.5rem; font-weight: bold; }
        .room-card { border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; background-color: #ffffff; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
        .stDataFrame { border: 1px solid #e0e0e0; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ฟังก์ชันประมวลผลข้อมูล ---

def process_master_files(files):
    """จัดการไฟล์รายชื่อนักเรียน โดยเน้นการกำจัดชื่อซ้ำ"""
    levels_db = {}
    for f in files:
        try:
            name = f.name.replace('.xlsx', '').replace('.csv', '')
            level_match = re.search(r'(ม\.\d+)', name)
            level = level_match.group(1) if level_match else "ระดับอื่นๆ"
            
            df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
            
            # ค้นหาคอลัมน์ เลขที่ และ ชื่อ
            c_sid = next((c for c in df.columns if "เลขที่" in str(c)), None)
            c_name = next((c for c in df.columns if any(k in str(c) for k in ["ชื่อ", "นามสกุล"])), None)
            
            if c_sid and c_name:
                df_clean = df[[c_sid, c_name]].copy()
                # แปลงเลขที่ให้เป็นตัวเลขและลบค่าว่าง
                df_clean[c_sid] = pd.to_numeric(df_clean[c_sid], errors='coerce')
                df_clean = df_clean.dropna(subset=[c_sid])
                df_clean[c_sid] = df_clean[c_sid].astype(int)
                df_clean.columns = ['เลขที่', 'ชื่อ - นามสกุล']
                
                # ✨ จุดสำคัญ 1: กำจัดชื่อซ้ำในไฟล์รายชื่อ (ป้องกันเด็กชื่อโผล่ 2 บรรทัด)
                df_clean = df_clean.drop_duplicates(subset=['เลขที่'], keep='first')
                
                if level not in levels_db: levels_db[level] = {}
                levels_db[level][name] = df_clean
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดกับไฟล์รายชื่อ {f.name}: {e}")
    return levels_db

def process_padlet_files(files):
    """จัดการไฟล์ Padlet โดยยุบรวมงานของเลขที่เดียวกัน"""
    all_data = []
    for f in files:
        try:
            df = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
            col_sec = next((c for c in df.columns if any(k in str(c).lower() for k in ["ส่วน", "section", "ห้อง"])), None)
            
            for _, row in df.iterrows():
                content_str = " ".join(map(str, row.values))
                sid_match = re.search(r'(?:เลขที่|No\.|#|n)\s*(\d+)', content_str, re.I)
                act_match = re.search(r'1\.(\d{1,2})', content_str)
                
                if sid_match and act_match:
                    all_data.append({
                        'เลขที่': int(sid_match.group(1)),
                        'กิจกรรม': f"1.{act_match.group(1)}",
                        'ห้อง_padlet': str(row[col_sec]).strip() if col_sec else ""
                    })
        except: continue
        
    if not all_data: return pd.DataFrame()
    
    df_padlet = pd.DataFrame(all_data)
    
    # ✨ จุดสำคัญ 2: ยุบรวมข้อมูล (Pivot) โดยใช้ max 
    # เพื่อให้คนส่งซ้ำหลายครั้งในกิจกรรมเดียว เหลือแค่สถานะ "ส่งแล้ว (1)" เท่านั้น
    pivot = df_padlet.pivot_table(
        index=['เลขที่', 'ห้อง_padlet'], 
        columns='กิจกรรม', 
        aggfunc='max', # ถ้ามีค่ามากกว่า 0 ให้เอาค่าสูงสุด (คือ 1) แถวจะได้ไม่แตก
        fill_value=0
    ).reset_index()
    
    return pivot

# --- 3. ส่วนแสดงผล ---

def main():
    inject_custom_css()
    st.markdown('<div class="main-header"><h1>📋 ระบบเช็คงานครูตระกูล v9.8.2</h1><p>แก้ไขปัญหารายชื่อซ้ำ และจัดระเบียบข้อมูลห้องเรียน</p></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    m_files = col1.file_uploader("📂 1. อัปโหลดไฟล์รายชื่อ (ม.1 - ม.3)", accept_multiple_files=True)
    p_files = col2.file_uploader("📂 2. อัปโหลดไฟล์จาก Padlet", accept_multiple_files=True)

    if m_files and p_files:
        levels_db = process_master_files(m_files)
        pivot_padlet = process_padlet_files(p_files)
        
        if not pivot_padlet.empty:
            full_acts = [f"1.{i}" for i in range(1, 15)] # กิจกรรม 1.1 - 1.14

            for level in sorted(levels_db.keys()):
                st.markdown(f'<div class="level-section">📚 ระดับชั้น {level}</div>', unsafe_allow_html=True)
                
                for room_full_name, df_student in levels_db[level].items():
                    # สกัดเฉพาะตัวเลขห้อง เช่น "31" หรือ "301" เพื่อไป Match กับข้อมูล Padlet
                    room_digits = "".join(re.findall(r'\d+', room_full_name))
                    
                    # กรองข้อมูลจาก Padlet ให้ตรงกับห้องนั้นๆ
                    df_room_padlet = pivot_padlet[pivot_padlet['ห้อง_padlet'].str.contains(room_digits, na=False)].copy()
                    
                    # ✨ จุดสำคัญ 3: รวมร่างข้อมูลแบบ Left Join 
                    # และใช้ drop_duplicates อีกรอบเพื่อความมั่นใจ 100%
                    final_df = df_student.merge(df_room_padlet, on='เลขที่', how='left').fillna(0)
                    final_df = final_df.drop_duplicates(subset=['เลขที่'], keep='first')
                    
                    # เพิ่มคอลัมน์กิจกรรมที่หายไปให้ครบ 1.1 - 1.14
                    for a in full_acts:
                        if a not in final_df.columns: final_df[a] = 0
                    
                    # คำนวณยอดรวม
                    final_df['รวมส่ง'] = final_df[full_acts].sum(axis=1)
                    final_df = final_df.sort_values('เลขที่')

                    # แสดงผล UI ห้องเรียน
                    with st.expander(f"🏫 รายละเอียดห้อง: {room_full_name} (นักเรียน {len(df_student)} คน)", expanded=True):
                        st.markdown(f"**สถานะการส่งงาน:**")
                        
                        # ตกแต่งตาราง
                        def style_status(val):
                            if isinstance(val, (int, float)) and val >= 1: return 'background-color: #e8f5e9; color: #2e7d32; text-align: center;'
                            return 'color: #ef9a9a; text-align: center;'

                        st.dataframe(
                            final_df[['เลขที่', 'ชื่อ - นามสกุล'] + full_acts + ['รวมส่ง']].style
                            .applymap(style_status, subset=full_acts)
                            .format({a: lambda x: '✔' if x >= 1 else '✘' for a in full_acts}),
                            use_container_width=True, hide_index=True
                        )
                        
                        # ปุ่มดาวน์โหลด
                        buf = BytesIO()
                        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
                            final_df.to_excel(writer, index=False, sheet_name='รายงาน')
                        st.download_button(f"📥 โหลด Excel {room_full_name}", buf.getvalue(), f"Report_{room_full_name}.xlsx", key=f"dl_{room_full_name}")
        else:
            st.error("❌ ไม่สามารถดึงข้อมูลจากไฟล์ Padlet ได้ กรุณาตรวจสอบว่ามีข้อความ 'เลขที่' และ '1.x' ในไฟล์หรือไม่")
    else:
        st.info("💡 กรุณาอัปโหลดไฟล์ให้ครบทั้ง 2 ช่อง เพื่อเริ่มการประมวลผลครับ")

if __name__ == "__main__":
    main()
