import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import base64

# ==========================================
# 1. SETUP & STYLING
# ==========================================
st.set_page_config(page_title="Ocular Microbiology Portal", page_icon="🏥", layout="wide")

# CSS to hide default menu and style buttons to look 'Blue & Professional'
st.markdown("""
<style>
    /* Main Background and Button Styling */
    .stApp { background-color: #FFFFFF; }
    div.stButton > button {
        background-color: #007BFF; color: white; border-radius: 8px; border: none; padding: 10px 24px;
    }
    div.stButton > button:hover {
        background-color: #0056b3; color: white;
    }
    /* Login Box Styling */
    .login-container {
        padding: 30px; border-radius: 10px; background-color: #F0F8FF;
        border: 1px solid #007BFF; text-align: center; margin-top: 50px;
    }
    h1, h2, h3 { color: #004085; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ROBUST DATABASE (Users + Data)
# ==========================================
def init_db():
    conn = sqlite3.connect('microbio_prod.db')
    c = conn.cursor()
    
    # 1. Users Table (Real Security)
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, pin TEXT, role TEXT, full_name TEXT)''')
    
    # 2. Requests Table
    c.execute('''CREATE TABLE IF NOT EXISTS requests 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, doctor_user TEXT, 
                  centre_name TEXT, patient_id TEXT, eye TEXT, sample TEXT, duration TEXT, 
                  meds TEXT, impression TEXT, stain TEXT, image_blob BLOB, status TEXT)''')
    
    # 3. Reports Table
    c.execute('''CREATE TABLE IF NOT EXISTS reports 
                 (req_id INTEGER PRIMARY KEY, rc_code TEXT, lab_id TEXT, quality TEXT, 
                  suitability TEXT, report TEXT, comments TEXT, auth_by TEXT)''')

    # Seed Admin Users if empty (For first run)
    c.execute("SELECT count(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users VALUES ('dr_satyam', '1234', 'Doctor', 'Dr. Satyam')")
        c.execute("INSERT INTO users VALUES ('lab_main', '5678', 'Lab', 'Central Lab Tech')")
        conn.commit()
    
    conn.close()

def check_login(user, pin):
    conn = sqlite3.connect('microbio_prod.db')
    c = conn.cursor()
    c.execute("SELECT role, full_name FROM users WHERE username=? AND pin=?", (user, pin))
    result = c.fetchone()
    conn.close()
    return result

# ==========================================
# 3. HELPER: SMART INPUT (Dropdown + Free Text)
# ==========================================
def smart_input(label, options, key_prefix):
    """Creates a dropdown with an 'Other' option that triggers a text box."""
    selection = st.selectbox(label, options + ["Other (Specify)"], key=f"{key_prefix}_sel")
    if selection == "Other (Specify)":
        return st.text_input(f"Please specify {label}", key=f"{key_prefix}_txt")
    return selection

# ==========================================
# 4. PDF ENGINE
# ==========================================
class MedicalReport(FPDF):
    def header(self):
        # Logo placeholder (draw a blue box if no image)
        self.set_fill_color(0, 123, 255)
        self.rect(0, 0, 210, 20, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'OCULAR MICROBIOLOGY REPORT', 0, 1, 'C')
        self.ln(10)

def generate_pdf(req, rep):
    pdf = MedicalReport()
    pdf.add_page()
    pdf.set_text_color(0, 0, 0)
    
    # Patient Info Box
    pdf.set_fill_color(240, 248, 255) # Light blue
    pdf.rect(10, 30, 190, 40, 'F')
    pdf.set_y(35)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(95, 8, f"Patient ID: {req[4]}", 0, 0)
    pdf.cell(95, 8, f"Date: {req[1]}", 0, 1)
    pdf.cell(95, 8, f"Centre: {req[3]}", 0, 0)
    pdf.cell(95, 8, f"Eye: {req[5]}", 0, 1)
    
    # Clinical Info
    pdf.ln(15)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 64, 133)
    pdf.cell(0, 10, "Clinical Details", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 11)
    
    details = [
        f"Sample: {req[6]}",
        f"Duration: {req[7]}",
        f"Medications: {req[8]}",
        f"Impression: {req[9]}",
        f"Stain: {req[10]}"
    ]
    for det in details:
        pdf.cell(0, 8, det, 0, 1)
        
    # Lab Report
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(0, 64, 133)
    pdf.cell(0, 10, "Microbiology Findings", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 11)
    
    pdf.multi_cell(0, 8, f"Report: {rep[5]}")
    if rep[6]: pdf.multi_cell(0, 8, f"Comments: {rep[6]}")
    
    pdf.ln(15)
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, f"Authorized By: {rep[7]} (Lab ID: {rep[2]})", 0, 1, 'R')
    
    return pdf.output(dest='S').encode('latin-1')

# ==========================================
# 5. UI VIEWS
# ==========================================
def login_view():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<div class='login-container'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3063/3063176.png", width=80)
        st.title("Secure Portal Login")
        
        u = st.text_input("Username")
        p = st.text_input("PIN", type="password")
        
        if st.button("Access System"):
            user_data = check_login(u, p)
            if user_data:
                st.session_state.update({
                    'logged_in': True, 'role': user_data[0], 
                    'name': user_data[1], 'user_id': u
                })
                st.rerun()
            else:
                st.error("Access Denied")
        st.markdown("</div>", unsafe_allow_html=True)

def doctor_view():
    st.sidebar.markdown(f"## 👤 {st.session_state['name']}")
    page = st.sidebar.radio("Navigation", ["Submit Sample", "My Reports"])
    
    if page == "Submit Sample":
        st.title("📝 New Patient Request")
        st.markdown("---")
        
        with st.form("main_form"):
            # Section 1: Demographics
            st.markdown("### 1. Patient Demographics")
            c1, c2, c3 = st.columns(3)
            pid = c1.text_input("Patient ID (Required)")
            cen = c2.text_input("Centre Name")
            eye = c3.selectbox("Eye", ["OD", "OS", "OU", "NA"])
            
            # Section 2: Clinical (Smart Inputs)
            st.markdown("### 2. Clinical History")
            col_a, col_b = st.columns(2)
            
            with col_a:
                sample = smart_input("Sample Type", ["Corneal Scraping"], "samp")
                dur_val = st.slider("Duration (Value)", 1, 30, 1)
                dur_unit = st.selectbox("Unit", ["Days", "Weeks", "Months"])
                duration = f"{dur_val} {dur_unit}"

            with col_b:
                meds_opts = st.multiselect("Current Meds", ["Antibiotics", "Antifungals", "Steroids"])
                meds_other = st.text_input("Other Meds (Free Text)")
                final_meds = ", ".join(meds_opts) + (f", {meds_other}" if meds_other else "")
            
            # Section 3: Tech
            st.markdown("### 3. Microbiology Details")
            imp = smart_input("Clinical Impression", 
                              ["Bacterial", "Fungal", "Acanthamoeba", "Viral"], "imp")
            stain = st.multiselect("Stain Required", ["Gram", "KOH", "Giemsa"])
            img = st.file_uploader("Upload Slide Image", type=['jpg', 'png'])
            
            if st.form_submit_button("📤 Submit for Analysis"):
                if pid and img:
                    conn = sqlite3.connect('microbio_prod.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO requests (timestamp, doctor_user, centre_name, patient_id, eye, sample, duration, meds, impression, stain, image_blob, status) VALUES (?,?,?,?,?,?,?,?,?,?,?, 'Pending')",
                              (datetime.now().strftime("%Y-%m-%d"), st.session_state['user_id'], cen, pid, eye, sample, duration, final_meds, imp, ", ".join(stain), img.getvalue()))
                    conn.commit()
                    conn.close()
                    st.success("Request Submitted Successfully!")
                else:
                    st.warning("Patient ID and Image are required.")

    elif page == "My Reports":
        st.title("📂 Completed Reports")
        conn = sqlite3.connect('microbio_prod.db')
        reqs = pd.read_sql(f"SELECT * FROM requests WHERE doctor_user='{st.session_state['user_id']}' AND status='Completed'", conn)
        
        if reqs.empty:
            st.info("No reports ready yet.")
        else:
            for idx, row in reqs.iterrows():
                with st.expander(f"✅ {row['patient_id']} - {row['timestamp']}"):
                    reps = pd.read_sql(f"SELECT * FROM reports WHERE req_id={row['id']}", conn).iloc[0]
                    st.write(f"**Diagnosis:** {reps['report']}")
                    
                    pdf_data = generate_pdf(row, reps)
                    st.download_button("⬇️ Download Official PDF", pdf_data, 
                                       file_name=f"Report_{row['patient_id']}.pdf", 
                                       mime='application/pdf')

def lab_view():
    st.sidebar.markdown(f"## 🔬 {st.session_state['name']}")
    st.title("Microbiology Lab Queue")
    
    conn = sqlite3.connect('microbio_prod.db')
    pending = pd.read_sql("SELECT * FROM requests WHERE status='Pending'", conn)
    conn.close()
    
    if pending.empty:
        st.success("All caught up! No pending slides.")
        return

    for idx, row in pending.iterrows():
        with st.expander(f"🔬 PENDING: {row['patient_id']} ({row['centre_name']})", expanded=True):
            c1, c2 = st.columns([1, 2])
            c1.image(row['image_blob'], caption="Microscopy Slide", use_column_width=True)
            
            with c2:
                st.info(f"Impression: {row['impression']} | Eye: {row['eye']}")
                st.write(f"**History:** {row['duration']}, Meds: {row['meds']}")
                
                with st.form(f"lab_form_{row['id']}"):
                    st.markdown("#### Enter Findings")
                    rc = st.text_input("Reading Centre Code")
                    lid = st.text_input("Lab ID")
                    qual = st.select_slider("Photo Quality", ["Bad", "Moderate", "Good"])
                    suit = smart_input("Suitability", ["Yes", "No"], f"suit_{row['id']}")
                    
                    rep_text = st.text_area("Detailed Report Interpretation")
                    auth = st.selectbox("Authorized By", ["Tech A", "Tech B", "Dr. Sharma"])
                    
                    if st.form_submit_button("✅ Release Report"):
                        conn = sqlite3.connect('microbio_prod.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO reports VALUES (?,?,?,?,?,?,?,?)",
                                  (row['id'], rc, lid, qual, suit, rep_text, "", auth))
                        c.execute(f"UPDATE requests SET status='Completed' WHERE id={row['id']}")
                        conn.commit()
                        conn.close()
                        st.rerun()

# ==========================================
# 6. MAIN APP LOOP
# ==========================================
init_db()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login_view()
else:
    if st.sidebar.button("🚪 Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
        
    if st.session_state['role'] == 'Doctor':
        doctor_view()
    else:
        lab_view()