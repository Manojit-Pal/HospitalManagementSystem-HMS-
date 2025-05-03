from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import uuid
import os
import google.generativeai as genai
from dotenv import load_dotenv
from flask import jsonify
from datetime import datetime, timedelta, date
import pytz

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set. Chatbot will return an error.")
    
try:
    genai.configure(api_key=GEMINI_API_KEY)
    
    model = genai.GenerativeModel(
    'gemini-2.0-flash',
    system_instruction="You are a helpful assistant for a hospital management system dashboard. Your purpose is to answer questions about the system's features, provide explanations related to dashboard metrics (like patient counts, bed availability), and offer general, non-medical advice. **Do not provide medical diagnoses, medical advice, or engage in off-topic conversations like telling jokes.** If a user asks for medical advice or asks about sensitive patient data, politely state that you cannot help with that and suggest they consult a medical professional or the appropriate system feature."
)
    print("Gemini model initialized successfully using gemini-2.0-flash.")
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    model = None 

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')
DATABASE = 'hospital.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def close_db(conn):
    if conn:
        conn.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        print('Initialized the database.')

@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()

@app.before_request
def require_login():
    
    protected_routes = [
        'dashboard', 'view_profile',
        'list_patients', 'add_patient', 'join_opd_queue', 'view_opd_queue',
        'list_beds', 'add_bed', 'list_admissions', 'admit_patient',
        'view_inventory', 'add_inventory_item', 'get_inventory_chart_data',
        'get_system_stats', 'get_recent_activities',
        'update_opd_status',
        'get_now_serving','chatbot_send_message',
        'get_admissions_data','get_daily_opd_by_department',
        'get_monthly_opd_by_department',
        'deduct_inventory_item','discharge_patient','get_low_stock_items','add_existing_inventory_item'
    ]

    allowed_routes = ['index', 'login', 'register', 'static', 'create_admin']

    if request.endpoint is None:
        return 

    if request.endpoint not in allowed_routes and 'user_id' not in session and request.endpoint in protected_routes:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        name = request.form.get('name')
        phone = request.form.get('phone')

        extra = {}
        provided_passcode = None 

        if user_type == 'hospital':
            extra['hospital_name'] = request.form.get('hospital_name')
            extra['location'] = request.form.get('location')
            provided_passcode = request.form.get('passcode')
        elif user_type == 'doctor':
            extra['specialization'] = request.form.get('specialization')
            extra['experience'] = request.form.get('experience')
            provided_passcode = request.form.get('passcode') 
        elif user_type == 'patient':
            extra['age'] = request.form.get('age')
            extra['gender'] = request.form.get('gender')

        error = None

        
        if not user_type:
            error = 'User type is required.'
        elif not name: 
             error = 'Name is required.'
        elif not phone: 
             error = 'Phone is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            
            error = 'Passwords do not match.'
        elif len(password) < 8:
            
            error = 'Password must be at least 8 characters long.'
        
        elif user_type == 'hospital' and (not extra.get('hospital_name') or not extra.get('location')):
             error = 'Hospital Name and Location are required for Hospital registration.'
        elif user_type == 'doctor' and (not extra.get('specialization') or extra.get('experience') is None): 
             error = 'Specialization and Experience are required for Doctor registration.'
        elif user_type == 'patient' and (extra.get('age') is None or not extra.get('gender')): 
             error = 'Age and Gender are required for Patient registration.'


        if not error:
             try: 
                existing = cursor.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
                if existing:
                    error = 'Email already registered.'
             except sqlite3.Error as e:
                 error = f'Database error checking email: {e}'
                 print(f"Database error during email check: {e}") 


        if not error and user_type in ['doctor', 'hospital']:
            stored_passcode = None

            if user_type == 'doctor':
                
                stored_passcode = os.getenv('DOCTOR_REGISTER_PASSCODE')
            elif user_type == 'hospital':
                stored_passcode = os.getenv('HOSPITAL_REGISTER_PASSCODE')

            
            if stored_passcode is None:
                 
                 print(f"ERROR: Registration passcode for {user_type.upper()}_REGISTER_PASSCODE is NOT set in environment variables!")
                 error = "Registration for this user type is currently unavailable. Please contact the system administrator." 

            elif provided_passcode != stored_passcode:
                error = 'Invalid registration passcode.'
            
            elif not provided_passcode: 
                 error = 'Registration passcode is required.'

        
        if error:
            flash(error, 'danger')
            close_db(conn) 
            return render_template('register.html')

        try:
            
            password_hash = generate_password_hash(password)

            cursor.execute(
                'INSERT INTO users (email, password_hash, user_type) VALUES (?,?,?)',
                (email, password_hash, user_type)
            )

            user_id = cursor.lastrowid

            if user_type == 'hospital':
                cursor.execute(
                    'INSERT INTO hospital_profiles (user_id, hospital_name, location) VALUES (?,?,?)',
                    (user_id, extra['hospital_name'], extra['location'])
                )
            elif user_type == 'doctor':
                cursor.execute(
                    'INSERT INTO doctor_profiles (user_id, specialization, experience) VALUES (?,?,?)',
                    (user_id, extra['specialization'], extra['experience'])
                )
            elif user_type == 'patient':
                 cursor.execute(
                    'INSERT INTO patient_profiles (user_id, age, gender) VALUES (?,?,?)',
                    (user_id, extra['age'], extra['gender'])
                 )

            conn.commit() 

            session.clear() 
            session['user_id'] = user_id
            session['user_email'] = email 
            session['user_type'] = user_type 

            flash('Registration successful! You are now logged in.', 'success')
            return redirect(url_for('index'))

        except sqlite3.Error as e:
            
            flash(f'Database error during registration: {e}', 'danger')
            conn.rollback() 
            print(f"Database error during registration: {e}") 
            
            return render_template('register.html')

        finally:

            close_db(conn)

    close_db(conn) 
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        error = None
        conn = get_db()
        cursor = conn.cursor()
        user = cursor.execute(
            'SELECT * FROM users WHERE email=? AND user_type=?',
            (email, user_type)
        ).fetchone()
        if user is None or not check_password_hash(user['password_hash'], password):
            error = 'Invalid credentials.'
        if error:
            flash(error, 'danger')
            close_db(conn)
            return render_template('login.html')

        session.clear()
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        session['user_type'] = user['user_type']
        flash(f'Logged in as {user["email"]}', 'success')
        close_db(conn)
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
def view_profile():

    user_id = session.get('user_id')
    user_type = session.get('user_type')

    if not user_id or not user_type:
        
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    user_data = None
    profile_data = None
    error = None

    try:
        
        user_data = cursor.execute(
            'SELECT id, email, user_type FROM users WHERE id = ?', (user_id,)
        ).fetchone()

        if not user_data:
            error = 'User not found.' 

        if not error:
            if user_type == 'hospital':
                profile_data = cursor.execute(
                    'SELECT hospital_name, location FROM hospital_profiles WHERE user_id = ?', (user_id,)
                ).fetchone()
                
            elif user_type == 'doctor':
                 profile_data = cursor.execute(
                    'SELECT specialization, experience FROM doctor_profiles WHERE user_id = ?', (user_id,)
                ).fetchone()
                
            elif user_type == 'patient':
                 profile_data = cursor.execute(
                    'SELECT age, gender FROM patient_profiles WHERE user_id = ?', (user_id,)
                ).fetchone()
                

            if profile_data:
                
                 user_info = dict(user_data)
                 user_info.update(dict(profile_data))
            else:
                
                 user_info = dict(user_data)
                 flash(f'No profile data found for user type: {user_type}', 'warning')

    except sqlite3.Error as e:
        error = f'Database error fetching profile: {e}'
        print(f"Database error fetching profile for user_id {user_id}: {e}")
    except Exception as e:
         error = f'An unexpected error occurred: {e}'
         print(f"Unexpected error fetching profile for user_id {user_id}: {e}")
    finally:
        close_db(conn)

    if error:
        flash(error, 'danger')
        
        return redirect(url_for('index'))

    return render_template('profile.html', user=user_info)


@app.route('/create_admin')
def create_admin():
    conn = get_db()
    cursor = conn.cursor()
    password_hash = generate_password_hash('admin123')
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, user_type) VALUES (?, ?, ?)",
            ('admin@hms.com', password_hash, 'admin'),
        )
        conn.commit()
        message = "Admin user created."
    except sqlite3.IntegrityError:
        message = "Admin user already exists."
    finally:
        close_db(conn)
    return message

@app.route('/patients/add', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form.get('age')
        gender = request.form.get('gender')
        contact_number = request.form.get('contact_number')
        address = request.form.get('address')
        emergency_contact = request.form.get('emergency_contact')
        blood_group = request.form.get('blood_group')
        medical_history = request.form.get('medical_history')
        patient_id = str(uuid.uuid4())

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO patients (patient_id, name, age, gender, contact_number, address, emergency_contact, blood_group, medical_history) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (patient_id, name, age, gender, contact_number, address, emergency_contact, blood_group, medical_history))
            conn.commit()
        except sqlite3.Error as e:
            flash(f"Error adding patient: {e}", "danger")
        finally:
            close_db(conn)
        return redirect(url_for('list_patients'))
    return render_template('add_patient.html')

@app.route('/patients')
def list_patients():
    conn = get_db()
    patients = conn.execute("SELECT * FROM patients").fetchall()
    close_db(conn)
    return render_template('list_patients.html', patients=patients)


@app.route('/opd/join', methods=['GET', 'POST'])
def join_opd_queue():
    

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT patient_id, name FROM patients ORDER BY name ASC")
        patients = cursor.fetchall() 

        existing_departments_raw = cursor.execute("SELECT DISTINCT department FROM opd_queue WHERE department IS NOT NULL AND department != '' ORDER BY department ASC").fetchall()
        existing_departments = [row['department'] for row in existing_departments_raw]

    except sqlite3.Error as e:
        print(f"Database error fetching data for join OPD queue form: {e}")
        flash(f"Error loading form options: {e}", "danger")
        patients = [] 
        existing_departments = [] 
    finally:
        
        close_db(conn)


    if request.method == 'POST':
        
        patient_id = request.form.get('patient_id') 
        department_select = request.form.get('department_select')
        department_other = request.form.get('department_other')
        department = department_other if department_select == 'other' else department_select
        error = None

        if not patient_id:
            error = "Please select a patient."
        elif not department: 
             error = "Please select or enter a department."


        if error:
            flash(error, 'danger')
            conn = get_db()
            cursor = conn.cursor()
            try:
                 cursor.execute("SELECT patient_id, name FROM patients ORDER BY name ASC")
                 patients = cursor.fetchall()
                 cursor.execute("SELECT DISTINCT department FROM opd_queue WHERE department IS NOT NULL AND department != '' ORDER BY department ASC").fetchall()
                 existing_departments_raw = cursor.execute("SELECT DISTINCT department FROM opd_queue WHERE department IS NOT NULL AND department != '' ORDER BY department ASC").fetchall()
                 existing_departments = [row['department'] for row in existing_departments_raw]
            except sqlite3.Error as e:
                 print(f"Database error fetching data for re-rendering join OPD queue form: {e}")
                 patients = []
                 existing_departments = []
            finally:
                 close_db(conn)

            return render_template('join_opd_queue.html',
                                   patients=patients,
                                   existing_departments=existing_departments,
                                   selected_patient_id=patient_id, 
                                   selected_department_select=department_select, 
                                   selected_department_other=department_other)


        conn = get_db()
        cursor = conn.cursor()
        try:
            
            utc = pytz.timezone('UTC')
            kolkata_tz = pytz.timezone('Asia/Kolkata')

            now_kolkata = datetime.now(kolkata_tz) 
            today_start_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end_kolkata = now_kolkata.replace(hour=23, minute=59, second=59, microsecond=999999)

            today_start_utc = today_start_kolkata.astimezone(utc)
            today_end_utc = today_end_kolkata.astimezone(utc)

            today_start_str = today_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            today_end_str = today_end_utc.strftime('%Y-%m-%d %H:%M:%S')

            
            existing_entry_count = cursor.execute(
                """
                SELECT COUNT(*) FROM opd_queue
                WHERE patient_id = ? AND department = ?
                AND status IN ('Waiting', 'Serving') -- Or check for any status other than 'Completed'/'Skipped'
                AND check_in_time BETWEEN ? AND ?
                """,
                (patient_id, department, today_start_str, today_end_str)
            ).fetchone()[0]

            if existing_entry_count > 0:
                error = f'Patient is already in the {department} OPD queue for today.'

        except sqlite3.Error as e:
            error = f'Database error during duplicate check: {e}'
            print(f"Database error during OPD queue duplicate check: {e}")
        except Exception as e:
            error = f'An unexpected error occurred during duplicate check: {e}'
            print(f"Unexpected error during OPD queue duplicate check: {e}")

        if error:
            flash(error, 'danger')
           
            conn = get_db()
            cursor = conn.cursor()
            try:
                 cursor.execute("SELECT patient_id, name FROM patients ORDER BY name ASC")
                 patients = cursor.fetchall()
                 existing_departments_raw = cursor.execute("SELECT DISTINCT department FROM opd_queue WHERE department IS NOT NULL AND department != '' ORDER BY department ASC").fetchall()
                 existing_departments = [row['department'] for row in existing_departments_raw]
            except sqlite3.Error as e:
                 print(f"Database error fetching data for re-rendering join OPD queue form: {e}")
                 patients = []
                 existing_departments = []
            finally:
                 close_db(conn)

            return render_template('join_opd_queue.html',
                                   patients=patients,
                                   existing_departments=existing_departments,
                                   selected_patient_id=patient_id,
                                   selected_department_select=department_select,
                                   selected_department_other=department_other)


        try:
            queue_id = str(uuid.uuid4())

            cursor.execute("SELECT MAX(token_number) FROM opd_queue WHERE department = ?", (department,))
            result = cursor.fetchone()[0]
            next_token = (result + 1) if result is not None else 1

            cursor.execute(
                "INSERT INTO opd_queue (queue_id, patient_id, department, token_number, status, check_in_time) VALUES (?, ?, ?, ?, ?, ?)",
                (queue_id, patient_id, department, next_token, 'Waiting', datetime.now(pytz.timezone('UTC')).strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.commit()
            flash(f"Successfully joined the {department} OPD queue with Token Number {next_token}.", "success")

        except sqlite3.Error as e:
            flash(f"Error joining queue: {e}", "danger")
            conn.rollback() 
        except Exception as e:
             flash(f"An unexpected error occurred while joining queue: {e}", "danger")
             print(f"Unexpected error during OPD queue insertion: {e}")
        finally:
            close_db(conn)

        return redirect(url_for('view_opd_queue'))

    
    return render_template('join_opd_queue.html',
                           patients=patients,
                           existing_departments=existing_departments)



@app.route('/opd')
def view_opd_queue():
    conn = get_db()
    cursor = conn.cursor()

    selected_department = request.args.get('department', 'All')

    try:
        
        cursor.execute("SELECT DISTINCT department FROM opd_queue ORDER BY department ASC")
        departments = [row['department'] for row in cursor.fetchall()]

        display_departments = ['All'] + departments
        sql_query = """
            SELECT
                oq.queue_id,
                oq.token_number,
                p.name,
                oq.department,
                oq.status,
                oq.check_in_time
            FROM opd_queue oq
            JOIN patients p ON oq.patient_id = p.patient_id
        """
        query_params = []

        if selected_department != 'All':
            sql_query += " WHERE oq.department = ?"
            query_params.append(selected_department)

        sql_query += " ORDER BY oq.department ASC, oq.check_in_time ASC"

        cursor.execute(sql_query, query_params)
        queue_items = cursor.fetchall()

    except sqlite3.Error as e:
        print(f"Database error fetching OPD queue: {e}")
        flash(f"Error loading OPD queue: {e}", "danger")
        queue_items = []
        departments = []
        display_departments = ['All']
    finally:
        close_db(conn)

    grouped_queue = {}
    for item in queue_items:
        department = item['department']
        if department not in grouped_queue:
            grouped_queue[department] = []
        grouped_queue[department].append(item)

    can_manage_opd = session.get('user_type') in ['hospital', 'doctor']

    return render_template('view_opd_queue.html',
                           grouped_queue=grouped_queue,
                           can_manage_opd=can_manage_opd,
                           departments=display_departments,
                           selected_department=selected_department)


@app.route('/opd/update_status', methods=['POST'])
def update_opd_status():
    
    queue_id = request.form.get('queue_id')
    new_status = request.form.get('status')

    # Basic validation
    if not queue_id or not new_status or new_status not in ['Waiting', 'Serving', 'Completed', 'Skipped']:
        return jsonify({'success': False, 'message': 'Invalid request'}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE opd_queue SET status = ? WHERE queue_id = ?",
            (new_status, queue_id)
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Status updated successfully'})

    except sqlite3.Error as e:
        conn.rollback() 
        print(f"Database error updating OPD status: {e}")
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

    finally:
        close_db(conn)

@app.route('/beds/add', methods=['GET', 'POST'])
def add_bed():
    
    if session.get('user_type') != 'hospital':
        flash('You do not have permission to add beds.', 'danger')
        return redirect(url_for('index'))
    

    conn = None 
    cursor = None 

    try:
        conn = get_db()
        cursor = conn.cursor()
        existing_departments_raw = cursor.execute("SELECT DISTINCT department FROM opd_queue WHERE department IS NOT NULL AND department != '' ORDER BY department ASC").fetchall()
        existing_departments = [row['department'] for row in existing_departments_raw]
    except sqlite3.Error as e:
        print(f"Database error fetching departments for add bed form: {e}")
        flash(f"Error loading department options: {e}", "danger")
        existing_departments = [] 
    finally:

        if conn:
             close_db(conn)


    if request.method == 'POST':
        
        ward_select = request.form.get('ward_select')
        ward_other = request.form.get('ward_other')

        
        ward = ward_other if ward_select == 'other' else ward_select
        

        bed_number = request.form.get('bed_number') 
        bed_type = request.form.get('bed_type') 

        error = None
        if not ward:
            error = "Ward name is required."
        elif not bed_number:
            error = "Bed Number/ID is required."

        if error:
            flash(error, 'danger')
            conn = get_db()
            cursor = conn.cursor()
            try:
                existing_departments_raw = cursor.execute("SELECT DISTINCT department FROM opd_queue WHERE department IS NOT NULL AND department != '' ORDER BY department ASC").fetchall()
                existing_departments = [row['department'] for row in existing_departments_raw]
            except sqlite3.Error as e:
                print(f"Database error fetching departments for re-rendering add bed form: {e}")
                existing_departments = []
            finally:
                close_db(conn)

            return render_template('add_bed.html',
                                   existing_departments=existing_departments,
                                   selected_ward_select=ward_select, 
                                   selected_ward_other=ward_other, 
                                   selected_bed_number=bed_number, 
                                   selected_bed_type=bed_type) 


       
        conn = get_db() 
        cursor = conn.cursor()
        try:
            existing_bed = cursor.execute(
                "SELECT bed_id FROM beds WHERE ward = ? AND bed_number = ?",
                (ward, bed_number)
            ).fetchone()

            if existing_bed:
                error = f'A bed with Ward "{ward}" and Bed Number "{bed_number}" already exists.'

        except sqlite3.Error as e:
            error = f'Database error during duplicate bed check: {e}'
            print(f"Database error during duplicate bed check: {e}")
        except Exception as e:
             error = f'An unexpected error occurred during duplicate bed check: {e}'
             print(f"Unexpected error during duplicate bed check: {e}")

        if error:
            flash(error, 'danger')
            
            conn = get_db()
            cursor = conn.cursor()
            try:
                existing_departments_raw = cursor.execute("SELECT DISTINCT department FROM opd_queue WHERE department IS NOT NULL AND department != '' ORDER BY department ASC").fetchall()
                existing_departments = [row['department'] for row in existing_departments_raw]
            except sqlite3.Error as e:
                print(f"Database error fetching departments for re-rendering add bed form: {e}")
                existing_departments = []
            finally:
                close_db(conn)

            
            return render_template('add_bed.html',
                                   existing_departments=existing_departments,
                                   selected_ward_select=ward_select,
                                   selected_ward_other=ward_other,
                                   selected_bed_number=bed_number,
                                   selected_bed_type=bed_type)
        


        
        try:
            bed_id = str(uuid.uuid4()) 

            cursor.execute("INSERT INTO beds (bed_id, ward, bed_number, bed_type, status) VALUES (?, ?, ?, ?, ?)",
                           (bed_id, ward, bed_number, bed_type, 'Available')) 
            conn.commit()
            flash(f"New bed (Ward: {ward}, Bed No: {bed_number}) added successfully.", "success") 

        except sqlite3.Error as e:
            flash(f"Error adding bed: {e}", "danger")
            conn.rollback() 
        except Exception as e:
             flash(f"An unexpected error occurred while adding bed: {e}", "danger")
             print(f"Unexpected error during bed insertion: {e}")
        finally:
            close_db(conn)

        return redirect(url_for('list_beds'))

    return render_template('add_bed.html', existing_departments=existing_departments)


@app.route('/beds')
def list_beds():

    conn = None
    cursor = None
    beds_list = []

    selected_ward = request.args.get('ward', 'All')
    selected_status = request.args.get('status', 'All')


    possible_statuses = ['All', 'Available', 'Occupied']

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT ward FROM beds WHERE ward IS NOT NULL ORDER BY ward ASC")
        wards = [row['ward'] for row in cursor.fetchall()]

        display_wards = ['All'] + wards

        sql_query = """
            SELECT
                bed_id,
                ward,
                bed_number,
                bed_type,
                status,
                current_patient_id -- Keep this if you plan to show patient info later
            FROM beds
        """
        query_params = []
        conditions = []

        if selected_ward != 'All':
            conditions.append("ward = ?")
            query_params.append(selected_ward)

        if selected_status != 'All':
            conditions.append("status = ?")
            query_params.append(selected_status)

        if conditions:
            sql_query += " WHERE " + " AND ".join(conditions)

        sql_query += """
            ORDER BY
                CASE status
                    WHEN 'Available' THEN 1
                    WHEN 'Occupied' THEN 2
                    ELSE 3
                END ASC,
                ward ASC,
                bed_number ASC;
        """

        cursor.execute(sql_query, query_params)
        beds_list = cursor.fetchall()

    except sqlite3.Error as e:
        print(f"Database error fetching bed list: {e}")
        flash(f"Error loading bed availability: {e}", "danger")
        beds_list = []
        display_wards = ['All'] 

    except Exception as e:
        print(f"General error fetching bed list: {e}")
        flash(f"An unexpected error occurred while loading beds: {e}", "danger")
        beds_list = []
        display_wards = ['All']

    finally:
        if conn:
            close_db(conn)

    grouped_beds = {'Available': {}, 'Occupied': {}}

    for bed in beds_list:
        status = bed['status']
        ward = bed['ward']

        if status in grouped_beds:
            if ward not in grouped_beds[status]:
                grouped_beds[status][ward] = []
            grouped_beds[status][ward].append(bed)

    return render_template('list_beds.html',
                           grouped_beds=grouped_beds,
                           wards=display_wards,
                           selected_ward=selected_ward,
                           statuses=possible_statuses,
                           selected_status=selected_status)

@app.route('/admissions/add', methods=['GET', 'POST'])
def admit_patient():
    conn = get_db()
    patients = conn.execute("SELECT patient_id, name FROM patients").fetchall()
    beds = conn.execute("SELECT bed_id, ward, bed_number, bed_type FROM beds WHERE status = 'Available'").fetchall()
    close_db(conn)

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        bed_id = request.form['bed_id']
        admission_id = str(uuid.uuid4())

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO admissions (admission_id, patient_id, bed_id) VALUES (?, ?, ?)",
                           (admission_id, patient_id, bed_id))
            cursor.execute("UPDATE beds SET status = 'Occupied', current_patient_id = ? WHERE bed_id = ?",
                           (patient_id, bed_id))
            conn.commit()
        except sqlite3.Error as e:
            flash(f"Error admitting patient: {e}", "danger")
        finally:
            close_db(conn)
        return redirect(url_for('list_admissions'))
    return render_template('admit_patient.html', patients=patients, beds=beds)

@app.route('/admissions')
def list_admissions():
    conn = get_db()
    admissions = conn.execute("""
        SELECT a.admission_id, p.name AS patient_name, b.bed_id, a.admission_time, a.status
        FROM admissions a
        JOIN patients p ON a.patient_id = p.patient_id
        JOIN beds b ON a.bed_id = b.bed_id
    """).fetchall()
    close_db(conn)
    return render_template('list_admissions.html', admissions=admissions)

@app.route('/discharge_patient', methods=['POST'])
def discharge_patient():
    """Discharges a patient from an admission and makes the bed available."""
    
    if session.get('user_type') not in ['hospital', 'doctor']:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403 

    admission_id = request.form.get('admission_id')

    if not admission_id:
        return jsonify({'success': False, 'message': 'Admission ID is required'}), 400 

    conn = get_db()
    cursor = conn.cursor()

    try:
        conn.execute('BEGIN TRANSACTION')

        cursor.execute("""
            UPDATE admissions
            SET status = 'Completed'
            WHERE admission_id = ? AND status = 'Admitted'
        """, (admission_id,))

        if cursor.rowcount == 0:
            conn.execute('ROLLBACK') 
            current_admission = cursor.execute("SELECT status FROM admissions WHERE admission_id = ?", (admission_id,)).fetchone()
            if current_admission:
                
                return jsonify({'success': False, 'message': f'Admission is already in status: {current_admission["status"]}'}), 409 
            else:
                
                return jsonify({'success': False, 'message': 'Admission not found'}), 404 
        
        bed_row = cursor.execute("SELECT bed_id FROM admissions WHERE admission_id = ?", (admission_id,)).fetchone()

        if bed_row is None:
            
            conn.execute('ROLLBACK')
            print(f"Error: Bed ID not found for admission {admission_id} after successful status update.")
            return jsonify({'success': False, 'message': 'An internal error occurred (bed association missing).'}), 500


        bed_id = bed_row['bed_id']

        cursor.execute("""
            UPDATE beds
            SET status = 'Available'
            WHERE bed_id = ?
        """, (bed_id,))

        conn.execute('COMMIT')

        return jsonify({'success': True, 'message': 'Patient discharged and bed made available'})

    except Exception as e:
        
        conn.execute('ROLLBACK')
        print(f"Error during patient discharge: {e}")
        return jsonify({'success': False, 'message': 'An error occurred during discharge'}), 500 
    finally:
        
        close_db(conn)



@app.route('/inventory/add', methods=['GET', 'POST'])
def add_inventory_item():
    
    if session.get('user_type') != 'hospital':
        flash('You do not have permission to add inventory items.', 'danger')
        return redirect(url_for('view_inventory')) 
    conn = get_db()
    cursor = conn.cursor()

    try:
        existing_items_raw = cursor.execute("SELECT DISTINCT item_name FROM inventory ORDER BY item_name ASC").fetchall()
        existing_units_raw = cursor.execute("SELECT DISTINCT unit FROM inventory WHERE unit IS NOT NULL AND unit != '' ORDER BY unit ASC").fetchall()

        existing_items = [row['item_name'] for row in existing_items_raw]
        existing_units = [row['unit'] for row in existing_units_raw]

    except sqlite3.Error as e:
        print(f"Database error fetching existing inventory data: {e}")
        flash(f"Error loading inventory options: {e}", "danger")
        
        existing_items = []
        existing_units = []
    finally:
        
        close_db(conn)


    if request.method == 'POST':
        
        item_name_select = request.form.get('item_name_select')
        item_name_other = request.form.get('item_name_other')

        item_name = item_name_other if item_name_select == 'other' else item_name_select
        unit_select = request.form.get('unit_select')
        unit_other = request.form.get('unit_other')

        unit = unit_other if unit_select == 'other' else unit_select

        try:
            quantity = int(request.form.get('quantity'))
            if quantity <= 0:
                 raise ValueError("Quantity must be a positive integer.")
        except (ValueError, TypeError):
            flash("Invalid quantity. Please enter a positive whole number.", "danger")

            return render_template('add_inventory_item.html',
                                   existing_items=existing_items,
                                   existing_units=existing_units,
                                   
                                   item_name_select=item_name_select,
                                   item_name_other=item_name_other,
                                   unit_select=unit_select,
                                   unit_other=unit_other,
                                   quantity=request.form.get('quantity'))

        if not item_name:
             flash("Item name is required.", "danger")
             return render_template('add_inventory_item.html',
                                   existing_items=existing_items,
                                   existing_units=existing_units,
                                   item_name_select=item_name_select,
                                   item_name_other=item_name_other,
                                   unit_select=unit_select,
                                   unit_other=unit_other,
                                   quantity=request.form.get('quantity'))


        item_id = str(uuid.uuid4()) 
        conn = get_db() 
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO inventory (item_id, item_name, quantity, unit) VALUES (?, ?, ?, ?)",
                           (item_id, item_name, quantity, unit))
            conn.commit()
            flash(f"Inventory item '{item_name}' added successfully.", "success")
        except sqlite3.Error as e:
            flash(f"Error adding inventory item: {e}", "danger")
            conn.rollback() 
        finally:
            close_db(conn) 

        return redirect(url_for('view_inventory'))

    return render_template('add_inventory_item.html',
                           existing_items=existing_items,
                           existing_units=existing_units)



@app.route('/inventory')
def view_inventory():
    
    if 'user_id' not in session:
         flash("Please log in to view this page.", "warning")
         return redirect(url_for('login'))

    conn = get_db()
    inventory = [] 
    try:
        
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        inventory = cursor.execute("SELECT * FROM inventory ORDER BY item_name ASC").fetchall()
    except sqlite3.Error as e:
        print(f"Database error fetching inventory: {e}")
        flash(f"Error fetching inventory: {e}", "danger")
    finally:
        close_db(conn) 

    user_type = session.get('user_type')
    can_add_inventory = user_type == 'hospital'
    can_deduct_inventory = user_type in ['hospital', 'doctor']

    return render_template('view_inventory.html',
                           inventory=inventory,
                           can_add_inventory=can_add_inventory,
                           can_deduct_inventory=can_deduct_inventory,

                           g={'theme': session.get('theme', 'light')})



@app.route('/inventory/deduct', methods=['POST'])
def deduct_inventory_item():
    
    if session.get('user_type') not in ['hospital', 'doctor']:
        return jsonify({'success': False, 'message': 'Permission denied.'}), 403

    item_id = request.form.get('item_id')
    try:
        quantity_to_deduct = int(request.form.get('quantity'))
        if quantity_to_deduct <= 0:
            raise ValueError("Quantity must be positive.")
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid quantity.'}), 400

    if not item_id:
        return jsonify({'success': False, 'message': 'Item ID required.'}), 400

    conn = get_db()
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT quantity FROM inventory WHERE item_id = ?", (item_id,))
        result = cursor.fetchone()

        if result is None:
            return jsonify({'success': False, 'message': 'Item not found.'}), 404

        current_quantity = result['quantity']
        new_quantity = current_quantity - quantity_to_deduct

        if new_quantity < 0:
            return jsonify({'success': False, 'message': f'Insufficient stock. Only {current_quantity} available.'}), 400

        cursor.execute("UPDATE inventory SET quantity = ? WHERE item_id = ?", (new_quantity, item_id))
        conn.commit()

        return jsonify({'success': True, 'message': 'Quantity updated.', 'new_quantity': new_quantity})

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error deducting inventory: {e}")
        return jsonify({'success': False, 'message': 'Database error.'}), 500
    except Exception as e:
        conn.rollback()
        print(f"Error deducting inventory: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred.'}), 500
    finally:
        close_db(conn)


@app.route('/inventory/add_existing', methods=['POST'])
def add_existing_inventory_item():

    if session.get('user_type') != 'hospital':
        return jsonify({'success': False, 'message': 'Permission denied.'}), 403

    item_id = request.form.get('item_id')
    try:
        quantity_to_add = int(request.form.get('quantity'))
        if quantity_to_add <= 0:
            raise ValueError("Quantity must be positive.")
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid quantity.'}), 400

    if not item_id:
        return jsonify({'success': False, 'message': 'Item ID required.'}), 400

    conn = get_db()
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    try:

        cursor.execute("SELECT quantity FROM inventory WHERE item_id = ?", (item_id,))
        result = cursor.fetchone()
        if result is None:
            return jsonify({'success': False, 'message': 'Item not found.'}), 404

        cursor.execute("UPDATE inventory SET quantity = quantity + ? WHERE item_id = ?",
                       (quantity_to_add, item_id))

        cursor.execute("SELECT quantity FROM inventory WHERE item_id = ?", (item_id,))
        updated_result = cursor.fetchone()
        new_quantity = updated_result['quantity'] if updated_result else None

        conn.commit()

        if new_quantity is not None:
            
            return jsonify({'success': True, 'message': 'Quantity updated.', 'new_quantity': new_quantity})
        else:
            
            conn.rollback() 
            return jsonify({'success': False, 'message': 'Failed to confirm update.'}), 500

    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error adding to inventory: {e}")
        return jsonify({'success': False, 'message': 'Database error.'}), 500
    except Exception as e: 
        conn.rollback()
        print(f"Error adding to inventory: {e}")
        return jsonify({'success': False, 'message': 'An unexpected error occurred.'}), 500
    finally:
        close_db(conn)


@app.route('/inventory/chart-data')
def get_inventory_chart_data():
    """Fetches inventory data (item names and quantities) for charting."""

    conn = get_db()
    try:
        
        inventory_data = conn.execute("""
            SELECT item_name, quantity
            FROM inventory
            WHERE quantity > 0 -- Only show items with quantity > 0 on the chart
            ORDER BY item_name ASC
        """).fetchall()

        labels = [row['item_name'] for row in inventory_data]
        data = [row['quantity'] for row in inventory_data]

        return jsonify({'labels': labels, 'data': data})

    except sqlite3.Error as e:
        print(f"Database error fetching inventory chart data: {e}")
        return jsonify({'error': 'Error fetching inventory data', 'details': str(e)}), 500
    finally:
        close_db(conn)

LOW_STOCK_THRESHOLD = 10

@app.route('/inventory/low-stock')
def get_low_stock_items():
    """
    Fetches inventory items with quantity below the defined threshold.
    Restricted to 'hospital' users.
    """

    if session.get('user_type') != 'hospital':
        
        return jsonify({'error': 'Unauthorized', 'message': 'You do not have permission to view low stock items.'}), 403

    conn = get_db()
    try:
        
        low_stock_items = conn.execute("""
            SELECT item_id, item_name, quantity, unit
            FROM inventory
            WHERE quantity <= ?
            ORDER BY quantity ASC, item_name ASC
        """, (LOW_STOCK_THRESHOLD,)).fetchall()

        items_list = [dict(row) for row in low_stock_items]

        low_stock_count = len(items_list)

        return jsonify({'low_stock_items': items_list, 'count': low_stock_count})

    except sqlite3.Error as e:
        print(f"Database error fetching low stock items: {e}")
        return jsonify({'error': 'Database Error', 'message': f'Error fetching low stock data: {e}'}), 500
    finally:
        close_db(conn)


@app.route('/get_system_stats', methods=['GET'])
def get_system_stats():
    conn = get_db()
    cursor = conn.cursor()
    stats = {}

    try:
    
        total_patients_row = cursor.execute("SELECT COUNT(*) FROM patients").fetchone()
        stats['total_patients'] = total_patients_row[0] if total_patients_row and total_patients_row[0] is not None else 0

        available_beds_row = cursor.execute("SELECT COUNT(*) FROM beds WHERE status = 'Available'").fetchone()
        stats['available_beds'] = available_beds_row[0] if available_beds_row and available_beds_row[0] is not None else 0

        utc = pytz.timezone('UTC')
        kolkata_tz = pytz.timezone('Asia/Kolkata') 
        now_server = datetime.now()
        now_kolkata = now_server.astimezone(kolkata_tz)

        today_start_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_kolkata = now_kolkata.replace(hour=23, minute=59, second=59, microsecond=999999) 

        today_start_utc = today_start_kolkata.astimezone(utc)
        today_end_utc = today_end_kolkata.astimezone(utc)

        today_start_str = today_start_utc.strftime('%Y-%m-%d %H:%M:%S')
        today_end_str = today_end_utc.strftime('%Y-%m-%d %H:%M:%S')

        print(f"\n--- Debugging /get_system_stats ---")
        print(f"  Server Local Time Now: {now_server}")
        print(f"  Kolkata Time Now: {now_kolkata}")
        print(f"  Kolkata Today Start: {today_start_kolkata}")
        print(f"  Kolkata Today End: {today_end_kolkata}")
        print(f"  UTC Today Start for Query: {today_start_utc}")
        print(f"  UTC Today End for Query: {today_end_utc}")
        print(f"  Querying for Appointments Today between (UTC strings):")
        print(f"  Start String: '{today_start_str}'")
        print(f"  End String:   '{today_end_str}'")


        appointments_today_row = cursor.execute(
            "SELECT COUNT(*) FROM opd_queue WHERE check_in_time BETWEEN ? AND ?",
            (today_start_str, today_end_str)
        ).fetchone()
        stats['appointments_today'] = appointments_today_row[0] if appointments_today_row and appointments_today_row[0] is not None else 0

        print(f"  Database count for today: {stats['appointments_today']}")
        print(f"--- End Debugging ---\n")


        return jsonify(stats)

    except sqlite3.Error as e:
        print(f"Database error fetching stats: {e}")
        return jsonify({'error': 'Could not fetch system statistics', 'details': str(e)}), 500 
    except Exception as e: 
         print(f"General error fetching stats: {e}")
         return jsonify({'error': 'Could not fetch system statistics', 'details': str(e)}), 500

    finally:
        close_db(conn)


@app.route('/get_recent_activities', methods=['GET'])
def get_recent_activities():
    conn = get_db()
    cursor = conn.cursor()
    recent_data = {}

    try:
        
        recent_patients = cursor.execute(
            "SELECT patient_id, name FROM patients ORDER BY patient_id DESC LIMIT 5"
        ).fetchall()
        recent_data['patients'] = [dict(row) for row in recent_patients] 

        recent_admissions_raw = cursor.execute(
            "SELECT a.admission_id, p.name AS patient_name, a.admission_time FROM admissions a JOIN patients p ON a.patient_id = p.patient_id ORDER BY a.admission_time DESC LIMIT 5"
        ).fetchall()

        recent_admissions_processed = []
        utc = pytz.timezone('UTC') 
        kolkata_tz = pytz.timezone('Asia/Kolkata') 

        for row in recent_admissions_raw:
            admission = dict(row)
            raw_admission_time_str = admission['admission_time']

            try:
                
                if '.' in raw_admission_time_str:
                     admission_time_utc_naive = datetime.strptime(raw_admission_time_str, '%Y-%m-%d %H:%M:%S.%f')
                else:
                    admission_time_utc_naive = datetime.strptime(raw_admission_time_str, '%Y-%m-%d %H:%M:%S')

                admission_time_utc_aware = utc.localize(admission_time_utc_naive)
                admission_time_kolkata = admission_time_utc_aware.astimezone(kolkata_tz)
                formatted_admission_time = admission_time_kolkata.strftime('%b %d, %Y %I:%M %p %Z')
                admission['admission_time'] = formatted_admission_time

            except (ValueError, TypeError) as e:
                 print(f"Error parsing or converting admission time '{raw_admission_time_str}': {e}")
                 admission['admission_time'] = 'Invalid Time' 

            recent_admissions_processed.append(admission)

        recent_data['admissions'] = recent_admissions_processed


        return jsonify(recent_data)

    except sqlite3.Error as e:
        print(f"Database error fetching recent activities: {e}")
        return jsonify({'error': 'Could not fetch recent activities', 'details': str(e)}), 500
    except Exception as e: 
        print(f"General error fetching recent activities: {e}")
        return jsonify({'error': 'Could not fetch recent activities', 'details': str(e)}), 500

    finally:
        close_db(conn)


@app.route('/get_now_serving', methods=['GET'])
def get_now_serving():
    conn = get_db()
    cursor = conn.cursor()
    serving_data = []

    try:
       
        serving_tokens = cursor.execute(
            "SELECT department, token_number FROM opd_queue WHERE status = 'Serving' ORDER BY department, token_number"
        ).fetchall()

        serving_data = [dict(row) for row in serving_tokens]

        return jsonify(serving_data)

    except sqlite3.Error as e:
        print(f"Database error fetching now serving data: {e}")
        return jsonify({'error': 'Could not fetch now serving data', 'details': str(e)}), 500

    finally:
        close_db(conn)



@app.route('/get_admissions_data', methods=['GET'])
def get_admissions_data():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        utc = pytz.timezone('UTC')
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        now_kolkata = datetime.now(kolkata_tz)
        today_start_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date_kolkata = today_start_kolkata - timedelta(days=4)
        today_end_kolkata = now_kolkata.replace(hour=23, minute=59, second=59, microsecond=999999)
        end_date_kolkata = today_end_kolkata
        start_date_utc = start_date_kolkata.astimezone(utc)
        end_date_utc = end_date_kolkata.astimezone(utc)

        start_date_utc_str = start_date_utc.strftime('%Y-%m-%d %H:%M:%S')
        end_date_utc_str = end_date_utc.strftime('%Y-%m-%d %H:%M:%S.%f')

        date_labels_kolkata = [(start_date_kolkata + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(5)]

        query = """
            SELECT
                DATE(admission_time) AS admission_date,
                COUNT(*) AS daily_admissions_count
            FROM
                admissions
            WHERE
                admission_time BETWEEN ? AND ? -- Filter using the calculated UTC range
            GROUP BY
                admission_date
            ORDER BY
                admission_date ASC;
        """

        cursor.execute(query, (start_date_utc_str, end_date_utc_str))
        admissions_from_db = cursor.fetchall()

        db_counts = {row['admission_date']: row['daily_admissions_count'] for row in admissions_from_db}

        final_admissions_data = {'labels': [], 'data': []}

        for date_str_kolkata in date_labels_kolkata:
             
             query_all = """
                 SELECT
                     admission_time -- Fetch the raw timestamp
                 FROM
                     admissions
                 WHERE
                     admission_time BETWEEN ? AND ? -- Filter using the calculated UTC range
                 ORDER BY
                     admission_time ASC;
             """
             cursor.execute(query_all, (start_date_utc_str, end_date_utc_str))
             all_admissions_raw = cursor.fetchall()

             daily_counts_kolkata = {date_str: 0 for date_str in date_labels_kolkata}

             for row in all_admissions_raw:
                 raw_admission_time_str = row['admission_time']

                 try:
                     
                     if '.' in raw_admission_time_str:
                         admission_time_utc_naive = datetime.strptime(raw_admission_time_str, '%Y-%m-%d %H:%M:%S.%f')
                     else:
                         admission_time_utc_naive = datetime.strptime(raw_admission_time_str, '%Y-%m-%d %H:%M:%S')

                     admission_time_utc_aware = utc.localize(admission_time_utc_naive)

                     admission_time_kolkata = admission_time_utc_aware.astimezone(kolkata_tz)

                     admission_date_kolkata_str = admission_time_kolkata.strftime('%Y-%m-%d')

                     if admission_date_kolkata_str in daily_counts_kolkata:
                         daily_counts_kolkata[admission_date_kolkata_str] += 1

                 except (ValueError, TypeError) as e:
                      print(f"Error parsing or converting admission time '{raw_admission_time_str}' for grouping: {e}")
                      

             final_admissions_data = {'labels': date_labels_kolkata, 'data': []}
             for date_str_kolkata in date_labels_kolkata:
                  final_admissions_data['data'].append(daily_counts_kolkata[date_str_kolkata]) 


             return jsonify(final_admissions_data)

    except sqlite3.Error as e:
        print(f"Database error fetching daily admissions data: {e}")
        
        return jsonify({'error': True, 'message': 'Could not fetch daily admissions data', 'details': str(e)}), 500
    except Exception as e:
        print(f"General error fetching daily admissions data: {e}")
        
        return jsonify({'error': True, 'message': 'An unexpected error occurred', 'details': str(e)}), 500
    finally:

        if conn:
            close_db(conn)


@app.route('/get_daily_opd_by_department', methods=['GET'])
def get_daily_opd_by_department():
    """Fetches OPD booking counts by department for the current day."""
    conn = None 
    try:
        conn = get_db()
        cursor = conn.cursor()

        utc = pytz.timezone('UTC')
        kolkata_tz = pytz.timezone('Asia/Kolkata')

        now_kolkata = datetime.now(kolkata_tz) 
        today_start_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_kolkata = now_kolkata.replace(hour=23, minute=59, second=59, microsecond=999999)

        today_start_utc = today_start_kolkata.astimezone(utc)
        today_end_utc = today_end_kolkata.astimezone(utc)

        today_start_str = today_start_utc.strftime('%Y-%m-%d %H:%M:%S')
        today_end_str = today_end_utc.strftime('%Y-%m-%d %H:%M:%S')

        query = """
            SELECT
                department,
                COUNT(*) AS department_count
            FROM
                opd_queue
            WHERE
                check_in_time BETWEEN ? AND ?
            GROUP BY
                department
            ORDER BY
                department ASC;
        """
        cursor.execute(query, (today_start_str, today_end_str))
        daily_opd_data = cursor.fetchall()

        labels = [row['department'] for row in daily_opd_data]
        data = [row['department_count'] for row in daily_opd_data]

        return jsonify({'labels': labels, 'data': data})

    except sqlite3.Error as e:
        print(f"Database error fetching daily OPD data: {e}")
        return jsonify({'error': True, 'message': 'Could not fetch daily OPD data', 'details': str(e)}), 500
    except Exception as e:
        print(f"General error fetching daily OPD data: {e}")
        return jsonify({'error': True, 'message': 'An unexpected error occurred', 'details': str(e)}), 500
    finally:
        if conn:
            close_db(conn)



@app.route('/get_monthly_opd_by_department', methods=['GET'])
def get_monthly_opd_by_department():
    """Fetches OPD booking counts by department for the last month."""
    conn = None 
    try:
        conn = get_db()
        cursor = conn.cursor()

        today = datetime.now().date()
        start_date = today - timedelta(days=30)

        start_date_str = start_date.strftime('%Y-%m-%d')
        today_str = today.strftime('%Y-%m-%d') 

        query = """
            SELECT
                department,
                COUNT(*) AS department_count
            FROM
                opd_queue
            WHERE
                DATE(check_in_time) BETWEEN ? AND ?
            GROUP BY
                department
            ORDER BY
                department ASC;
        """
        cursor.execute(query, (start_date_str, today_str))
        monthly_opd_data = cursor.fetchall()

        # Prepare data for Chart.js
        labels = [row['department'] for row in monthly_opd_data]
        data = [row['department_count'] for row in monthly_opd_data]

        return jsonify({'labels': labels, 'data': data})

    except sqlite3.Error as e:
        print(f"Database error fetching monthly OPD data: {e}")
        return jsonify({'error': True, 'message': 'Could not fetch monthly OPD data', 'details': str(e)}), 500
    except Exception as e:
        print(f"General error fetching monthly OPD data: {e}")
        return jsonify({'error': True, 'message': 'An unexpected error occurred', 'details': str(e)}), 500
    finally:
        if conn:
            close_db(conn)



@app.route('/chatbot/send_message', methods=['POST'])
def chatbot_send_message():
    """
    Receives message, checks for commands, gets data from DB if needed,
    manages history, and uses Gemini for general queries.
    """
    
    gemini_available = model is not None

    if request.method == 'POST':
        try:
            data = request.get_json()
            user_message_text = data.get('message')

            if not user_message_text:
                return jsonify({'response': 'Error: No message received.'}), 400 

            print(f"Received message: {user_message_text}")
            serializable_history = session.get('chat_history', [])
            serializable_history.append({'role': 'user', 'parts': [{'text': user_message_text}]})
            bot_response_text = None
            command_handled = False 
            user_message_lower = user_message_text.lower()

            try:
                
                 db = get_db()

                 if "total patients" in user_message_lower or "number of patients" in user_message_lower:
                     print("Recognized command: total patients")
                     try:
                         
                         total_patients_row = db.execute('SELECT COUNT(*) FROM patients').fetchone()
                         total_patients = total_patients_row[0] if total_patients_row else 0
                         bot_response_text = f"There are currently {total_patients} patients in the system."
                         command_handled = True
                         print(f"Handled command: total patients, response: {bot_response_text}")
                     except Exception as db_error:
                         print(f"Database error fetching total patients: {db_error}")
                         import traceback
                         traceback.print_exc()
                         bot_response_text = "Sorry, I couldn't retrieve the patient count right now due to a database error."
                         command_handled = True

                 elif "available beds" in user_message_lower or "free beds" in user_message_lower:
                     print("Recognized command: available beds")
                     try:
                        
                         available_beds_row = db.execute('SELECT COUNT(*) FROM beds WHERE status = "Available"').fetchone() 
                         available_beds = available_beds_row[0] if available_beds_row else 0
                         bot_response_text = f"There are currently {available_beds} available beds."
                         command_handled = True
                         print(f"Handled command: available beds, response: {bot_response_text}")
                     except Exception as db_error:
                         print(f"Database error fetching available beds: {db_error}")
                         import traceback
                         traceback.print_exc()
                         bot_response_text = "Sorry, I couldn't retrieve the available bed count right now due to a database error."
                         command_handled = True


            except Exception as command_error:

                print(f"Error during command handling logic execution: {command_error}")
                import traceback
                traceback.print_exc()
                bot_response_text = "An internal error occurred while trying to process your command."
                command_handled = True 


            if not command_handled:
                 print("No command handled internally, sending to Gemini API...")
                 if not gemini_available:

                    bot_response_text = "Error: Chatbot service is currently unavailable."
                 else:
                     try:
                         
                         chat = model.start_chat(history=serializable_history)
                         response = chat.send_message(user_message_text)

                         if response and hasattr(response, 'text'):
                             bot_response_text = response.text
                             print("Response generated by Gemini.")
                         else:
                              print(f"Gemini API returned unexpected response structure: {response}")
                              import json
                              try:
                                  print(f"Gemini response object (attempted JSON): {json.dumps(response, default=str)}")
                              except TypeError:
                                   print(f"Gemini response object (raw): {response}")
                              bot_response_text = "Error: Could not get a valid response from the AI."

                     except Exception as api_error:
                         print(f"Error calling Gemini API for general query: {api_error}")
                         import traceback
                         traceback.print_exc()
                         bot_response_text = "Error: Could not get a response from the AI."
                         


            
            if bot_response_text is not None:
                 
                 serializable_history.append({'role': 'model', 'parts': [{'text': bot_response_text}]})
                 session['chat_history'] = serializable_history

            if bot_response_text is None:
                
                 bot_response_text = "Sorry, I didn't understand that or encountered an issue."

            return jsonify({'response': bot_response_text}), 200 


        except Exception as e:
            
            print(f"Fatal error in chatbot_send_message: {e}")
            import traceback
            traceback.print_exc()
            session.pop('chat_history', None)
            return jsonify({'response': 'Error: An unexpected error occurred on the server.'}), 500 

    return jsonify({'response': 'Error: Method not allowed.'}), 405


if __name__ == '__main__':
    app.run(debug=True)

# flask --app app.py --debug run