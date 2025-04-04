from fpdf import FPDF
import os
import streamlit as st
import sqlite3
from zipfile import ZipFile
import pandas as pd
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# Define DB_FILE at the top level
DB_FILE = 'students.db'
OTP_CODES = {}

def is_registered_email(email):
    """Check if the email exists in the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM staff WHERE email = ?", (email,))
        return cursor.fetchone() is not None

def send_otp(email):
    """Send OTP only if the email is registered in the database."""
    if not is_registered_email(email):
        st.error("❌ This email is not registered. Please use a valid email.")
        return False

    otp = str(random.randint(100000, 999999))  # Generate 6-digit OTP

    # Store OTP in session state
    if "otp_codes" not in st.session_state:
        st.session_state.otp_codes = {}

    st.session_state.otp_codes[email] = otp  # Save OTP for this email
    print(f"✅ DEBUG: Generated OTP for {email} -> {otp}")  # Debugging: Print OTP

    sender_email = "mmadhesh225@gmail.com"
    sender_password = "dysnbtxscrldtdnr"

    subject = "Your OTP Code for Login"
    body = f"Your OTP for login is: {otp}. It is valid for 5 minutes."

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, email, msg.as_string())
        server.quit()
        print("✅ OTP sent successfully!")  # Debugging
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False
#add

def get_courses():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('staff', 'generated_tcs', 'sqlite_sequence')")
        tables = [row[0] for row in cursor.fetchall()]

    return tables  # Return only table names

#download history
def init_download_history():
    """Creates a table to track TC downloads."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT,
                course TEXT,
                download_date TEXT,
                download_time TEXT,
                is_duplicate INTEGER DEFAULT 0
            )
        """)
        conn.commit()


# Initialize database and create tables if they don't exist
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        for table in ["BCA", "BScCS", "BScAI", "BScVisCom", "BScPsy", "BScNFSM", "BAEnglish", "BcomAF", "BcomBM", "BcomCS", "BcomCA", "BBA"]: #00000000000000000000000000000
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table}'
            """)
            if not cursor.fetchone():
                columns = [
                    "Name of the Pupil (in CAPITAL Letters)",
                    "Name of the Father / Mother",
                    "Nationality & Religion",
                    "Caste",
                    "Gender",
                    "Date of Birth as entered in the Higher Secondary TC",
                    "Date of admission",
                    "Course / Class admitted",
                    "Period of Study",
                    "Class in which the pupil was studying at the time of leaving (in words)",
                    "Language studied under Part I",
                    "Medium of Instruction",
                    "Whether qualified for promotion to higher class",
                    "Whether the student has paid all fees due to the college",
                    "Date on which the student actually left the college",
                    "The Student's Conduct & Character",
                    "Date of application for Transfer Certificate",
                    "Date of issue of the Transfer Certificate",
                    "serial_number",
                    "admission_number",
                    "batch"
                ]
                create_query = f"CREATE TABLE {table} ("
                create_query += ", ".join([f'"{col}" TEXT' for col in columns])
                create_query += ")"
                conn.execute(create_query)
                conn.commit()

class PDF(FPDF):
    def add_logo(self, path):
        self.image(path, x=22, y=20, w=165, h=28)

    def cell_with_wrapping(self, w, h, txt, border=0, ln=0, align='', fill=False):
        self.multi_cell(w, h, txt, border=border, align=align, fill=fill)
        if ln == 0:
            self.set_xy(self.get_x() + w, self.get_y() - h)
        elif ln == 1:
            self.ln(h)


def generate_tc(data, logo_path="sacas_logo_new.png"):
    try:
        # Check if the TC was already downloaded
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM download_history 
                WHERE student_name = ? AND course = ?
            """, (data.get("Name of the Pupil (in CAPITAL Letters)"), data.get("Course / Class admitted")))
            
            is_duplicate = cursor.fetchone()[0] > 0  # If count > 0, it's a duplicate

        pdf = PDF()
        pdf.add_page()
        page_width = pdf.w - 2 * pdf.l_margin
        half_page_width = (page_width / 2) - 10
        
        # **Step 1: Add Watermark First (if Duplicate)**
        if is_duplicate:
            pdf.set_font("Times", "B", 50)
            pdf.set_text_color(200, 200, 200)  # Light gray watermark
            pdf.rotate(45, x=105, y=148.5)  # Rotate around the center of A4 page
            pdf.text(60, 160, "DUPLICATE")  # Adjust text position
            pdf.rotate(0)  # Reset rotation
            pdf.set_text_color(0, 0, 0)  # Reset text color

        # **Step 2: Add Logo and Header**
        pdf.add_logo(logo_path)
        pdf.ln(39)
        pdf.set_font('Times', 'B', 10)
        pdf.cell(0, 5, "Poonamallee - Avadi Main Road, Thiruverkadu, Chennai - 600 077", ln=True, align="C")
        pdf.cell(0, 3, "Sponsored by:", ln=True, align="C")
        pdf.ln(2)
        pdf.set_font('Times', "B", 13)
        pdf.cell(0, 7, "DHARMA NAIDU EDUCATIONAL & CHARITABLE TRUST", ln=True, align="C")
        pdf.set_font('Times', "BU", 14)
        pdf.cell(0, 4, "TRANSFER CERTIFICATE", ln=True, align="C")

        pdf.set_font('Times', "B", 10)
        pdf.set_left_margin(16)

        pdf.cell(100, 10, f"Serial No.: {data.get('serial_number', '')}", 0, 0, 'L')
        pdf.set_x(55)
        pdf.cell(100, 10, f"Admission No.: {data.get('admission_number', '')}", 0, 0, 'C')
        pdf.set_x(-116)
        pdf.cell(100, 10, f"Batch: {data.get('batch', '')}", 0, 1, 'R')
        pdf.set_font('Times', "", 10)
        pdf.ln(2)

        # **Step 3: Add Student Information Fields**
        fields = [
            "Name of the Pupil (in CAPITAL Letters)",
            "Name of the Father / Mother",
            "Nationality & Religion",
            "Caste",
            "Gender",
            "Date of Birth as entered in the Higher Secondary TC",
            "Date of admission",
            "Course / Class admitted",
            "Period of Study",
            "Class in which the pupil was studying at the time of leaving (in words)",
            "Language studied under Part I",
            "Medium of Instruction",
            "Whether qualified for promotion to higher class",
            "Whether the student has paid all fees due to the college",
            "Date on which the student actually left the college",
            "The Student's Conduct & Character",
            "Date of application for Transfer Certificate",
            "Date of issue of the Transfer Certificate",
        ]

        for i, field in enumerate(fields, start=1):
            value = str(data.get(field, ""))
            pdf.cell_with_wrapping(half_page_width+3, 7, f"{i}. {field}", 0, 0, 'L')
            pdf.set_x(55)
            pdf.cell(100, 7, f":", 0, 0, 'C')
            pdf.set_x(107)
            pdf.cell(0, 7, f"{value}", 0, 1, 'L')
            pdf.ln(0.5)

        # **Step 4: Add Footer Section**
        pdf.ln(10)
        pdf.set_font('Times', 'B', 11)
        pdf.cell(100, 10, "College Seal", 0, 0, 'L')
        pdf.cell(0, 10, "PRINCIPAL                      ", ln=True, align="R")
        pdf.set_x(55)
        pdf.set_font('Times', 'B', 11)
        pdf.cell(100, 6, "DECLARATION", ln=True, align="C")
        pdf.set_font('Times', '', 11)
        pdf.cell(0, 10, "I hereby declare that the particulars against items 1 to 7 are correct and that no change will be demanded in future.", ln=True, align='L')
        pdf.set_font('Times', 'B', 11)
        pdf.ln(10)
        pdf.cell(0, 6, "Student's Signature with date        ", ln=True, align="R")

        # **Step 5: Ensure 'student_name' and 'course' exist**
        student_name = data.get("Name of the Pupil (in CAPITAL Letters)", "Unknown Student")
        course = data.get("Course / Class admitted", "Unknown Course")

        if not student_name or student_name == "Unknown Student":
            st.error("⚠️ Error: Missing student name in database. Cannot generate TC.")
            return None

        if not course or course == "Unknown Course":
            st.error("⚠️ Error: Missing course name in database. Cannot generate TC.")
            return None

        # **Step 6: Generate PDF**
        output_file = f"Transfer_Certificate_{data.get('Name of the Pupil (in CAPITAL Letters)', 'unknown')}.pdf"
        pdf.output(output_file, dest='F')

        # **Step 7: Log the Download in History**
        if os.path.exists(output_file):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO download_history (student_name, course, download_date, download_time, is_duplicate) 
                    VALUES (?, ?, DATE('now'), TIME('now'), ?)
                """, (student_name, course, int(is_duplicate)))
                conn.commit()
            return output_file
        else:
            st.error("File generation failed.")
            return None
    except Exception as e:
        st.error(f"Error generating file: {e}")
        return None




def create_table_from_excel(df, table_name):
    with sqlite3.connect(DB_FILE) as conn:
        # Ensure table names with dots or spaces are safely wrapped in double quotes
        table_name = table_name.strip().replace(" ", "_")  # ✅ Ensure consistency
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        columns = df.columns
        create_query = f'CREATE TABLE {table_name} ('
        create_query += ", ".join([f'"{col}" TEXT' for col in columns])
        create_query += ")"
        conn.execute(create_query)
        df.to_sql(table_name.strip('"'), conn, if_exists='replace', index=False)  # Strip quotes before using in Pandas
        st.success(f"✅ Successfully created table {table_name.strip('\"')} with {len(df)} records")

def upload_excel():
    st.title("Upload Excel Data")
    uploaded_file = st.file_uploader("Choose an Excel file", type=['xlsx', 'xls'])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip()  # Ensure clean column names
            st.write("Preview of uploaded data:")
            st.dataframe(df.head())

            # Fetch table names directly (no UI names)
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('staff', 'generated_tcs')")
                tables = [row[0] for row in cursor.fetchall()]

            courses = get_courses()
            if not courses:
                st.warning("⚠ No tables exist. Please create a course first.")
                table_name = None
            else:
                table_name = st.selectbox("Select table to create/update:", ["Select a Table"] + courses)
  # Show actual table names

            if st.button("Confirm Upload"):
                required_columns = [
                    "Name of the Pupil (in CAPITAL Letters)",
                    "Name of the Father / Mother",
                    "Nationality & Religion",
                    "Caste",
                    "Gender",
                    "Date of Birth as entered in the Higher Secondary TC",
                    "Date of admission",
                    "Course / Class admitted",
                    "Period of Study",
                    "Class in which the pupil was studying at the time of leaving (in words)",
                    "Language studied under Part I",
                    "Medium of Instruction",
                    "Whether qualified for promotion to higher class",
                    "Whether the student has paid all fees due to the college",
                    "Date on which the student actually left the college",
                    "The Student's Conduct & Character",
                    "serial_number",
                    "admission_number",
                    "batch"
                ]

                missing_columns = [col for col in required_columns if col.lower() not in map(str.lower, df.columns)]
                if missing_columns:
                    st.error(f"Missing required columns: {', '.join(missing_columns)}")
                    return

                create_table_from_excel(df, table_name)

        except Exception as e:
            st.error(f"Error processing Excel file: {e}")



def download_all_tcs(selected_tables):
    try:
        zip_file_name = "all_tcs.zip"
        with ZipFile(zip_file_name, "w") as zipf:
            with sqlite3.connect(DB_FILE) as conn:
                for table in selected_tables:
                    query = f'SELECT * FROM "{table_name}"'  # ✅ Correct SQL syntax

                    df = pd.read_sql_query(query, conn)
                    for _, row in df.iterrows():
                        file_name = generate_tc(row.to_dict())
                        if file_name:
                            zipf.write(file_name, os.path.basename(file_name))
        return zip_file_name
    except Exception as e:
        st.error(f"Error creating ZIP file: {e}")
        return None

 #course login    

def staff_login():
    """Handles staff login for Manage Courses"""
    if "manage_course_logged_in" not in st.session_state:
        st.session_state.manage_course_logged_in = False

    if not st.session_state.manage_course_logged_in:
        st.subheader("🔐 Staff Login Required")

        username = st.text_input("👤 Username")
        password = st.text_input("🔑 Password", type="password")

        if st.button("Login"):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM staff WHERE username=? AND password=?", (username, password))
                user = cursor.fetchone()

                if user:
                    st.success("✅ Login Successful!")
                    st.session_state.manage_course_logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ Invalid Credentials!")

def logout():
    """Logs out the user from Manage Courses"""
    st.session_state.manage_course_logged_in = False
    st.rerun()


#delete history
import smtplib
from email.mime.text import MIMEText
import sqlite3

# Email Configuration (Use App Password if using Gmail)
EMAIL_SENDER = "your-email@gmail.com"  # Replace with your email
EMAIL_PASSWORD = "your-app-password"  # Use an App Password for security

def fetch_staff_emails():
    """Fetch all staff emails from the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM staff")  # Ensure your 'staff' table has an 'email' column
        emails = [row[0] for row in cursor.fetchall()]
    return emails

def send_deletion_email(course_name):
    """Send an email to all staff when a department history is deleted."""
    staff_emails = fetch_staff_emails()
    if not staff_emails:
        print("❌ No staff emails found in the database. Skipping email notification.")
        return

    subject = f"📢 {course_name} Download History Deleted"
    body = f"The download history for the department '{course_name}' has been deleted.\n\nPlease check the system for details."

    # Email Configuration (Use App Password)
    sender_email = "mmadhesh225@gmail.com"  # Replace with your email
    sender_password = "dysnbtxscrldtdnr"  # Use Google App Password

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            
            for email in staff_emails:
                msg = MIMEText(body)
                msg["Subject"] = subject
                msg["From"] = sender_email
                msg["To"] = email

                server.sendmail(sender_email, email, msg.as_string())
                print(f"✅ Email sent to: {email}")  # Debug message

        print("✅ Email notification sent to all staff successfully.")
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication Error: Check your email and App Password.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")



def delete_download_history(course_name):
    """Deletes download history for a specific course (department)."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM download_history WHERE course = ?", (course_name,))
        conn.commit()

    send_deletion_email(course_name)  # Send email after deleting history



#view history    
def view_download_history():
    st.subheader("📜 Download History")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        courses = get_courses()
        selected_course = st.selectbox("Select Course", ["Select a Course"] + courses)

        if selected_course != "Select a Course":
            cursor.execute("""
                SELECT student_name, download_date, download_time, 
                       CASE WHEN is_duplicate = 1 THEN 'Yes' ELSE 'No' END AS duplicate_status 
                FROM download_history WHERE course = ?
            """, (selected_course,))
            data = cursor.fetchall()

            if data:
                df = pd.DataFrame(data, columns=["Student Name", "Download Date", "Download Time", "Is Duplicate"])
                st.dataframe(df)

                # **Delete History for Selected Course**
                if st.button(f"🗑 Delete {selected_course} Download History"):
                    delete_download_history(selected_course)  # Deletes history and sends email
                    st.success(f"✅ Download history for '{selected_course}' has been erased.")
                    st.rerun()  # Refresh page after deletion
            else:
                st.info(f"No download history found for **{selected_course}**.")



#000000000000000000000000000000000000000000

def add_course(course_name):
    """Creates a new course table in the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{course_name}'")
        if cursor.fetchone():
            st.warning(f"⚠️ Course '{course_name}' already exists.")
            return

        columns = [
            "Name of the Pupil (in CAPITAL Letters)",
            "Name of the Father / Mother",
            "Nationality & Religion",
            "Caste",
            "Gender",
            "Date of Birth as entered in the Higher Secondary TC",
            "Date of admission",
            "Course / Class admitted",
            "Period of Study",
            "Class in which the pupil was studying at the time of leaving (in words)",
            "Language studied under Part I",
            "Medium of Instruction",
            "Whether qualified for promotion to higher class",
            "Whether the student has paid all fees due to the college",
            "Date on which the student actually left the college",
            "The Student's Conduct & Character",
            "Date of application for Transfer Certificate",
            "Date of issue of the Transfer Certificate",
            "serial_number",
            "admission_number",
            "batch"
        ]
        create_query = f"CREATE TABLE {course_name} (" + ", ".join([f'"{col}" TEXT' for col in columns]) + ")"
        conn.execute(create_query)
        conn.commit()

    #st.success("✅ Course added successfully!")  # Simple success message



def delete_course(course_name):
    """Deletes an existing course table from the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{course_name}'")
        if not cursor.fetchone():
            st.warning(f"⚠️ Course '{course_name}' does not exist.")
            return

        conn.execute(f"DROP TABLE {course_name}")
        conn.commit()

    #st.success("✅ Course deleted successfully!")  # Simple success message


def staff_dashboard():
    st.title("📌 Staff Dashboard")

    # Tabs for different operations
    tab1, tab2, tab3, tab4, tab5= st.tabs(["📂 Upload Data", "📊 View Database", "📜 Download Certificates", "📜 Download History", "⚙️ Manage Courses"])

    # ---- Tab 1: Upload Excel Data ----
    with tab1:
        upload_excel()

    # ---- Tab 2: View Database ----
    with tab2:
        st.subheader("📊 View Student Records")

        courses = get_courses()
        selected_table = st.selectbox("Select Table to View", ["Select a Table"] + courses, key="view_table")

        if selected_table != "Select a Table":
            table_name = selected_table  # Use selected table directly

            with sqlite3.connect(DB_FILE) as conn:
                try:
                    query = f'SELECT * FROM "{table_name}"'  # ✅ Ensure correct SQL syntax
                    df = pd.read_sql_query(query, conn)

                    if not df.empty:
                        st.success(f"✅ Data retrieved successfully from `{table_name}`!")
                        st.dataframe(df)
                    else:
                        st.warning(f"⚠ No records found in `{table_name}`. Please upload data.")
                except Exception as e:
                    st.error(f"⚠ Error fetching data: {e}")

    # ---- Tab 3: Download Certificates ----
    # ---- Tab 3: Download Certificates ----
    with tab3:
        st.subheader("📄 Download Single Certificate")

        # Select course
        courses = get_courses()
        selected_table = st.selectbox("Select Table for Single TC", ["Select a Table"] + courses, key="download_single_tc")

        if selected_table != "Select a Table":
            table_name = selected_table  # ✅ Use table name directly

            with sqlite3.connect(DB_FILE) as conn:
                query = f'SELECT * FROM "{table_name}"'
                df = pd.read_sql_query(query, conn)

                if df.empty:
                    st.info(f"No data available in `{table_name}`. Please upload data first.")
                else:
                    names = df["Name of the Pupil (in CAPITAL Letters)"].tolist()

                    selected_name = st.selectbox("Select Student to Download TC", ["Select a Student"] + names, key="select_student_tc")

                    if selected_name != "Select a Student":
                        if st.button("Generate & Download Single TC"):
                            selected_row = df[df["Name of the Pupil (in CAPITAL Letters)"] == selected_name].iloc[0]
                            file_name = generate_tc(selected_row.to_dict())

                            if file_name:
                                with open(file_name, "rb") as f:
                                    st.download_button(
                                        label="📥 Download Transfer Certificate",
                                        data=f,
                                        file_name=file_name,
                                        mime="application/pdf",
                                    )

        # 📜 Download Transfer Certificates
        st.subheader("📜 Download Transfer Certificates")

        courses = get_courses()
        selected_table = st.selectbox("Select Course for Single TC", courses, key="download_course_tc")

        # Ensure a valid selection
        if selected_table and selected_table != "Select a Table":
            table_name = selected_table  # ✅ Use selected_table instead of undefined course

            with sqlite3.connect(DB_FILE) as conn:
                query = f'SELECT * FROM "{table_name}"'  # ✅ Correct SQL syntax
                df = pd.read_sql_query(query, conn)

                if df.empty:
                    st.info(f"No data available in `{table_name}`. Please upload data first.")
                    names = []  # ✅ Ensure names is always defined
                else:
                    names = df["Name of the Pupil (in CAPITAL Letters)"].tolist()

                # 🔹 Multi-select: Allow selecting multiple students
                selected_names = st.multiselect("Select Students to Download TC", names, key="multi_student_tc")

                if st.button("Generate & Download Selected TCs"):
                    if not selected_names:
                        st.warning("⚠ Please select at least one student.")
                    else:
                        zip_file_name = "selected_students_tcs.zip"
                        with ZipFile(zip_file_name, "w") as zipf:
                            for name in selected_names:
                                selected_row = df[df["Name of the Pupil (in CAPITAL Letters)"] == name].iloc[0]
                                file_name = generate_tc(selected_row.to_dict())

                                if file_name:
                                    zipf.write(file_name, os.path.basename(file_name))

                        # Provide download button for selected TCs as ZIP
                        with open(zip_file_name, "rb") as f:
                            st.download_button(
                                label="📥 Download Selected Transfer Certificates",
                                data=f,
                                file_name=zip_file_name,
                                mime="application/zip",
                            )

        # 📦 Download All Transfer Certificates (One ZIP for All)
        st.subheader("📦 Download All Transfer Certificates (One ZIP for All)")

        # Multi-select to choose multiple courses
        courses = get_courses()
        selected_courses = st.multiselect("Select Courses to Download All TCs:", courses, key="download_multiple_tcs")

        if st.button("Generate & Download All TCs"):
            if not selected_courses:
                st.warning("⚠ Please select at least one course.")
            else:
                main_zip_file = "All_Selected_Courses.zip"
                files_added = False  # ✅ Track if any TC files are added

                with ZipFile(main_zip_file, "w") as main_zip:
                    with sqlite3.connect(DB_FILE) as conn:
                        for course in selected_courses:
                            table_name = course  # ✅ Assign 'course' inside the loop

                            if not table_name:
                                st.error(f"⚠️ Error: Invalid course '{course}'. Skipping...")
                                continue  # Skip invalid courses

                            try:
                                query = f'SELECT * FROM "{table_name}"'  # ✅ Ensure correct SQL syntax
                                df = pd.read_sql_query(query, conn)

                                if df.empty:
                                    st.info(f"⚠ No data found for `{course}`. Skipping...")
                                    continue  # Skip if no student data is available

                                for _, row in df.iterrows():
                                    file_name = generate_tc(row.to_dict())
                                    if file_name:
                                        main_zip.write(file_name, arcname=f"{course}/{os.path.basename(file_name)}")
                                        files_added = True  # ✅ Mark that at least one TC was added

                            except Exception as e:
                                st.error(f"⚠️ Error retrieving data for `{course}`: {e}")
                                continue  # Skip to the next course

                # ✅ Only show the download button if at least one file was added
                if files_added:
                    with open(main_zip_file, "rb") as f:
                        st.download_button(
                            label="📥 Download All Courses in One ZIP",
                            data=f,
                            file_name=main_zip_file,
                            mime="application/zip",
                        )
                else:
                    st.warning("⚠ No valid Transfer Certificates found. ZIP file not generated.")
    with tab4:
        view_download_history()

    # ---- Tab 5: Manage Courses ----
    with tab5:
        st.subheader("⚙️ Manage Courses")

            # ---- Add New Course ----
        new_course = st.text_input("Enter New Course Name:")
        if st.button("➕ Add Course"):
            if new_course:
                add_course(new_course.replace(" ", ""))
                st.success(f"✅ Course '{new_course}' Added Successfully!")
            else:
                st.warning("⚠ Please enter a valid course name.")

            # ---- Delete Existing Course ----
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_courses = [row[0] for row in cursor.fetchall()]

        excluded_tables = {"generated_tcs", "staff", "sqlite_sequence"}
        filtered_courses = [course for course in existing_courses if course not in excluded_tables]

        if filtered_courses:
            course_to_delete = st.selectbox("Select Table to Delete:", ["Select a Table"] + filtered_courses, key="delete_course")

            if course_to_delete != "Select a Table":
                if st.button("🗑 Delete Course"):
                    delete_course(course_to_delete)
                    st.success(f"✅ Course '{course_to_delete}' Deleted Successfully!")
        else:
            st.info("ℹ️ No courses available to delete.")

            # ---- Logout Button ----
            #if st.button("🚪 Logout from Manage Courses"):
             #   st.session_state["manage_course_logged_in"] = False
              #  st.success("🔒 Logged out successfully!")
               # st.rerun()




def main():
    init_download_history()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>Staff Login</h2>", unsafe_allow_html=True)
        email = st.text_input("Enter your Email")

        if st.button("Send OTP"):
            if send_otp(email):
                st.session_state.email = email  # Save email for OTP verification
                st.session_state.otp_sent = True
                st.success("✅ OTP Sent! Check your email.")
            else:
                st.error("❌ Failed to send OTP.")

        if "otp_sent" in st.session_state and st.session_state.otp_sent:
            otp_input = st.text_input("Enter OTP")

            # Retrieve OTP from session state
            correct_otp = st.session_state.otp_codes.get(st.session_state.email, None)  

            print(f"🔍 DEBUG: Stored OTP = {correct_otp}, Entered OTP = {otp_input}")  # Debugging

            if st.button("Verify OTP"):
                if correct_otp and correct_otp == otp_input:
                    st.session_state.logged_in = True
                    st.session_state.otp_sent = False
                    st.success("✅ Login Successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid OTP")
    else:
        st.sidebar.title("Welcome!")
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.email = None
            st.session_state.otp_sent = False
            st.rerun()
        staff_dashboard() 


if __name__ == "__main__":
    main()
