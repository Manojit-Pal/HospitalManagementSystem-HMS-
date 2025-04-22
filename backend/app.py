from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import uuid
import os
import google.generativeai as genai
from dotenv import load_dotenv
from flask import jsonify # Make sure jsonify is imported at the top
from datetime import datetime, timedelta, date # Make sure datetime and date are imported
import pytz

load_dotenv()  # Load environment variables from .env

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set. Chatbot will return an error.")
    # In a production app, you might want to handle this more robustly

try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Configure the generative model
    # Choose a model that's suitable for your use case (e.g., 'gemini-pro')
    # Check Gemini documentation for available models and their capabilities
    model = genai.GenerativeModel(
    'gemini-2.0-flash', # Your chosen model
    system_instruction="You are a helpful assistant for a hospital management system dashboard. Your purpose is to answer questions about the system's features, provide explanations related to dashboard metrics (like patient counts, bed availability), and offer general, non-medical advice. **Do not provide medical diagnoses, medical advice, or engage in off-topic conversations like telling jokes.** If a user asks for medical advice or asks about sensitive patient data, politely state that you cannot help with that and suggest they consult a medical professional or the appropriate system feature."
    # Add other parameters like generation_config or safety_settings if needed
)
    print("Gemini model initialized successfully using gemini-2.0-flash.")
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    model = None # Set model to None if initialization fails
    # You might want to log this error more formally

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')  # Fallback if not set
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
    # Define routes that require login
    protected_routes = [
        'dashboard', 'view_profile', # <--- Add the endpoint name for your dashboard page here
        'list_patients', 'add_patient', 'join_opd_queue', 'view_opd_queue',
        'list_beds', 'add_bed', 'list_admissions', 'admit_patient',
        'view_inventory', 'add_inventory_item',
        'get_system_stats', 'get_recent_activities', # Keep these
        'update_opd_status', # Keep this
        'get_now_serving', # <--- Add this dashboard data endpoint
        'get_admissions_data' # <--- Add this dashboard data endpoint
    ]
    # Allow access to index, login, register, and static files
    # Keep 'index' in allowed_routes if your homepage (/) is NOT the protected dashboard
    allowed_routes = ['index', 'login', 'register', 'static', 'create_admin']

    # Add a check for None endpoint (e.g. during 404) for robustness
    if request.endpoint is None:
        return # Allow Flask to handle 404

    if request.endpoint not in allowed_routes and 'user_id' not in session and request.endpoint in protected_routes:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # DB connection needed early for email check or re-rendering on error
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        # Base user data
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Additional common info (optional fields can use .get)
        name = request.form.get('name')
        phone = request.form.get('phone')

        # Role-specific extra details + Passcode
        extra = {}
        provided_passcode = None # Initialize passcode variable

        if user_type == 'hospital':
            extra['hospital_name'] = request.form.get('hospital_name')
            extra['location'] = request.form.get('location')
            provided_passcode = request.form.get('passcode') # Get passcode if user_type is hospital
        elif user_type == 'doctor':
            extra['specialization'] = request.form.get('specialization')
            extra['experience'] = request.form.get('experience')
            provided_passcode = request.form.get('passcode') # Get passcode if user_type is doctor
        elif user_type == 'patient':
            extra['age'] = request.form.get('age')
            extra['gender'] = request.form.get('gender')

        # --- Start Server-Side Validation Checks ---
        error = None

        # Basic required fields validation
        # Adding checks for required 'extra' fields based on user_type here too
        if not user_type:
            error = 'User type is required.'
        elif not name: # Added validation for name
             error = 'Name is required.'
        elif not phone: # Added validation for phone
             error = 'Phone is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            # Note: Client-side JS also checks this, but server-side check is essential
            error = 'Passwords do not match.'
        elif len(password) < 8:
            # Note: Client-side JS also checks this via minlength, but server-side check is essential
            error = 'Password must be at least 8 characters long.'
        # Add checks for required fields in 'extra' based on user_type
        elif user_type == 'hospital' and (not extra.get('hospital_name') or not extra.get('location')):
             error = 'Hospital Name and Location are required for Hospital registration.'
        elif user_type == 'doctor' and (not extra.get('specialization') or extra.get('experience') is None): # Check for None specifically for number field
             error = 'Specialization and Experience are required for Doctor registration.'
        elif user_type == 'patient' and (extra.get('age') is None or not extra.get('gender')): # Check for None specifically for number field
             error = 'Age and Gender are required for Patient registration.'


        # Check if the email already exists in the database (only if no basic error)
        if not error:
             try: # Add try block for database check
                existing = cursor.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
                if existing:
                    error = 'Email already registered.'
             except sqlite3.Error as e:
                 error = f'Database error checking email: {e}'
                 print(f"Database error during email check: {e}") # Log error


        # --- Start Passcode Validation (only if no error so far and user_type is Doctor/Hospital) ---
        if not error and user_type in ['doctor', 'hospital']:
            stored_passcode = None # Initialize stored passcode

            if user_type == 'doctor':
                # Get the doctor passcode from environment variables
                stored_passcode = os.getenv('DOCTOR_REGISTER_PASSCODE')
            elif user_type == 'hospital':
                 # Get the hospital passcode from environment variables
                stored_passcode = os.getenv('HOSPITAL_REGISTER_PASSCODE')

            # Check if environment variable is set first
            if stored_passcode is None:
                 # This indicates a server configuration issue. Prevent registration.
                 print(f"ERROR: Registration passcode for {user_type.upper()}_REGISTER_PASSCODE is NOT set in environment variables!")
                 error = "Registration for this user type is currently unavailable. Please contact the system administrator." # User-friendly message
            # Check if provided passcode matches the stored one
            # For higher security, use `import hmac; hmac.compare_digest(provided_passcode, stored_passcode)`
            # Note: hmac.compare_digest requires both inputs to be bytes or strings of same length.
            # Simple comparison is likely sufficient for this project's scope.
            elif provided_passcode != stored_passcode:
                error = 'Invalid registration passcode.'
            # Optional: Check if passcode was expected but not provided (HTML 'required' helps, but server-side is safer)
            elif not provided_passcode: # Check if passcode was expected but not provided
                 error = 'Registration passcode is required.'

        # --- End Passcode Validation ---


        # --- End Server-Side Validation Checks ---


        # If any validation check failed (basic, email, or passcode)
        if error:
            flash(error, 'danger')
            close_db(conn) # Close DB before returning
            # Return the register.html template to display the error on the form
            return render_template('register.html')


        # If ALL validation checks pass, proceed with database insertion
        try:
            # Hash the password
            password_hash = generate_password_hash(password)

            # Insert into users table
            cursor.execute(
                'INSERT INTO users (email, password_hash, user_type) VALUES (?,?,?)',
                (email, password_hash, user_type)
            )
            # IMPORTANT: Do NOT commit yet. We need to commit user AND profile insertion together.
            # conn.commit() # <-- Remove this commit here!
            user_id = cursor.lastrowid # Get the ID of the newly registered user

            # Insert additional role-specific data based on user type
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

            conn.commit() # Commit the entire transaction (user + profile) at the end of the try block

            # Log the user in automatically after successful registration
            session.clear() # Clear any existing session
            session['user_id'] = user_id
            session['user_email'] = email # Store email in session
            session['user_type'] = user_type # Store user type in session

            flash('Registration successful! You are now logged in.', 'success')
            # close_db(conn) # Close DB before redirecting (handled in finally or just before return)
            return redirect(url_for('index')) # Redirect to the index/dashboard page

        except sqlite3.Error as e:
            # Catch any database errors during insertion
            flash(f'Database error during registration: {e}', 'danger')
            conn.rollback() # Rollback the entire transaction if anything failed
            print(f"Database error during registration: {e}") # Log server-side error
            # close_db(conn) # Close DB before returning (handled in finally)
            return render_template('register.html') # Re-render the page with error

        finally:
            # Ensure the database connection is closed in all cases after the POST request
            close_db(conn)


    # This block handles the initial GET request to display the empty registration form
    close_db(conn) # Close DB for the GET request
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
        # Login success
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
        # This case should ideally be caught by @app.before_request,
        # but adding a check here is robust.
        flash('Please log in to view your profile.', 'warning')
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    user_data = None
    profile_data = None
    error = None

    try:
        # Fetch base user data (email, user_type)
        user_data = cursor.execute(
            'SELECT id, email, user_type FROM users WHERE id = ?', (user_id,)
        ).fetchone()

        if not user_data:
            error = 'User not found.' # Should not happen if user_id is in session

        # Fetch role-specific profile data
        if not error:
            if user_type == 'hospital':
                profile_data = cursor.execute(
                    'SELECT hospital_name, location FROM hospital_profiles WHERE user_id = ?', (user_id,)
                ).fetchone()
                # Add 'name' here once you add it to the schema/users table
                # profile_data = cursor.execute(
                #     'SELECT u.email, p.hospital_name, p.location FROM users u JOIN hospital_profiles p ON u.id = p.user_id WHERE u.id = ?', (user_id,)
                # ).fetchone()
            elif user_type == 'doctor':
                 profile_data = cursor.execute(
                    'SELECT specialization, experience FROM doctor_profiles WHERE user_id = ?', (user_id,)
                ).fetchone()
                 # Add 'name' here once you add it to the schema/users table
                # profile_data = cursor.execute(
                #     'SELECT u.email, p.specialization, p.experience FROM users u JOIN doctor_profiles p ON u.id = p.user_id WHERE u.id = ?', (user_id,)
                # ).fetchone()
            elif user_type == 'patient':
                 profile_data = cursor.execute(
                    'SELECT age, gender FROM patient_profiles WHERE user_id = ?', (user_id,)
                ).fetchone()
                 # Add 'name' here once you add it to the schema/users table
                # profile_data = cursor.execute(
                #     'SELECT u.email, p.age, p.gender FROM users u JOIN patient_profiles p ON u.id = p.user_id WHERE u.id = ?', (user_id,)
                # ).fetchone()
            # Add elif blocks for other user types if any

            if profile_data:
                 # Combine user_data (email) with profile_data for easier template access
                 # Convert row objects to dictionaries for easier merging
                 user_info = dict(user_data)
                 user_info.update(dict(profile_data))
            else:
                 # Handle case where user_type exists but no profile data found (shouldn't happen with current register logic)
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
        # Redirect or render an error page
        return redirect(url_for('index')) # Or a dedicated error page

    # Render the profile template, passing the combined user_info
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
    cursor = conn.cursor() # Get a cursor for executing queries

    # Fetch patients for the GET request or in case of a POST error
    patients = cursor.execute("SELECT patient_id, name FROM patients").fetchall()
    # Beds list is not needed here, but keeping the connection open for now

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        department = request.form['department']

        # --- Start Constraint Check: Prevent Duplicate Entry Same Day/Department ---
        error = None

        try:
            # 1. Get today's date range in the target timezone (Asia/Kolkata)
            #    and convert to UTC for the database query, similar to get_system_stats
            utc = pytz.timezone('UTC')
            kolkata_tz = pytz.timezone('Asia/Kolkata') # Define India/Kolkata timezone (IST)

            now_kolkata = datetime.now(kolkata_tz) # Get current time in Kolkata
            today_start_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end_kolkata = now_kolkata.replace(hour=23, minute=59, second=59, microsecond=999999)

            today_start_utc = today_start_kolkata.astimezone(utc)
            today_end_utc = today_end_kolkata.astimezone(utc)

            today_start_str = today_start_utc.strftime('%Y-%m-%d %H:%M:%S')
            today_end_str = today_end_utc.strftime('%Y-%m-%d %H:%M:%S') # Adjust format if your DB stores higher precision

            # 2. Check if the patient already has an entry in the queue for this department today
            #    We check if the status is NOT 'Completed' or 'Skipped', meaning they are
            #    currently waiting, being served, or somehow still active in the queue.
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

        # --- End Constraint Check ---

        if error:
            flash(error, 'danger')
            # Close DB and return to the form, passing the patients list
            close_db(conn)
            return render_template('join_opd_queue.html', patients=patients)


        # If no error, proceed with adding the patient to the queue
        try:
            queue_id = str(uuid.uuid4())

            # Get the next token number for the department
            cursor.execute("SELECT MAX(token_number) FROM opd_queue WHERE department = ?", (department,))
            result = cursor.fetchone()[0]
            next_token = (result + 1) if result is not None else 1

            # Insert the new queue entry
            cursor.execute(
                "INSERT INTO opd_queue (queue_id, patient_id, department, token_number) VALUES (?, ?, ?, ?)",
                (queue_id, patient_id, department, next_token)
            )
            conn.commit()
            flash('Successfully joined the OPD queue.', 'success')

        except sqlite3.Error as e:
            flash(f"Error joining queue: {e}", "danger")
            conn.rollback() # Rollback the insert if it failed
        finally:
            close_db(conn)

        # Redirect to the queue view regardless of whether insertion succeeded after the check
        return redirect(url_for('view_opd_queue'))

    # For GET request or if POST handling returns before redirect
    close_db(conn) # Close DB after fetching patients for GET
    return render_template('join_opd_queue.html', patients=patients)

# Modify this route in your app.py

@app.route('/opd/queue')
def view_opd_queue():
    conn = get_db()
    queue_entries = conn.execute("""
        SELECT q.queue_id, q.token_number, p.name, q.department, q.status, q.check_in_time
        FROM opd_queue q
        JOIN patients p ON q.patient_id = p.patient_id
        ORDER BY q.token_number
    """).fetchall()
    close_db(conn)

    # Check if the logged-in user is a doctor or hospital
    can_manage_opd = session.get('user_type') in ['doctor', 'hospital']

    # Pass the flag to the template
    return render_template('view_opd_queue.html', queue=queue_entries, can_manage_opd=can_manage_opd)

# Add a new route to handle status updates
@app.route('/opd/update_status', methods=['POST'])
def update_opd_status():
    # This route requires a logged-in doctor or hospital user (handled by @app.before_request)
    # The @app.before_request function should be updated to protect this route

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
        conn.rollback() # Rollback changes if there's an error
        print(f"Database error updating OPD status: {e}")
        return jsonify({'success': False, 'message': f'Database error: {e}'}), 500

    finally:
        close_db(conn)

@app.route('/beds/add', methods=['GET', 'POST'])
def add_bed():
    if request.method == 'POST':
        ward = request.form['ward']
        bed_number = request.form['bed_number']
        bed_type = request.form.get('bed_type')
        bed_id = str(uuid.uuid4())

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO beds (bed_id, ward, bed_number, bed_type) VALUES (?, ?, ?, ?)",
                           (bed_id, ward, bed_number, bed_type))
            conn.commit()
        except sqlite3.Error as e:
            flash(f"Error adding bed: {e}", "danger")
        finally:
            close_db(conn)
        return redirect(url_for('list_beds'))
    return render_template('add_bed.html')

@app.route('/beds')
def list_beds():
    conn = get_db()
    beds = conn.execute("SELECT * FROM beds").fetchall()
    close_db(conn)
    return render_template('list_beds.html', beds=beds)

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

@app.route('/inventory/add', methods=['GET', 'POST'])
def add_inventory_item():
    if request.method == 'POST':
        item_name = request.form['item_name']
        quantity = int(request.form['quantity'])
        unit = request.form.get('unit')
        item_id = str(uuid.uuid4())

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO inventory (item_id, item_name, quantity, unit) VALUES (?, ?, ?, ?)",
                           (item_id, item_name, quantity, unit))
            conn.commit()
        except sqlite3.Error as e:
            flash(f"Error adding inventory item: {e}", "danger")
        finally:
            close_db(conn)
        return redirect(url_for('view_inventory'))
    return render_template('add_inventory_item.html')

@app.route('/inventory')
def view_inventory():
    conn = get_db()
    inventory = conn.execute("SELECT * FROM inventory").fetchall()
    close_db(conn)
    return render_template('view_inventory.html', inventory=inventory)

@app.route('/get_system_stats', methods=['GET'])
def get_system_stats():
    conn = get_db()
    cursor = conn.cursor()
    stats = {}

    try:
        # 1. Get Total Number of Registered Patients
        total_patients_row = cursor.execute("SELECT COUNT(*) FROM patients").fetchone()
        stats['total_patients'] = total_patients_row[0] if total_patients_row and total_patients_row[0] is not None else 0

        # 2. Get Number of Available Beds
        available_beds_row = cursor.execute("SELECT COUNT(*) FROM beds WHERE status = 'Available'").fetchone()
        stats['available_beds'] = available_beds_row[0] if available_beds_row and available_beds_row[0] is not None else 0

        # 3. Get Number of Appointments Today
        # We need to get today's date in the correct format for comparison
        # Assuming check_in_time is stored as 'YYYY-MM-DD HH:MM:SS' in UTC by default CURRENT_TIMESTAMP
        # It's safest to work with timezones explicitly

        utc = pytz.timezone('UTC')
        kolkata_tz = pytz.timezone('Asia/Kolkata') # Define India/Kolkata timezone (IST)

        # Get today's date in the server's local time
        now_server = datetime.now()
        # Get today's date specifically for the Kolkata timezone
        now_kolkata = now_server.astimezone(kolkata_tz)

        # Calculate start and end of today in Kolkata time
        today_start_kolkata = now_kolkata.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end_kolkata = now_kolkata.replace(hour=23, minute=59, second=59, microsecond=999999) # Use 999999 to include the last microsecond

        # Convert these Kolkata times back to UTC for the database query
        today_start_utc = today_start_kolkata.astimezone(utc)
        today_end_utc = today_end_kolkata.astimezone(utc)

        # Format the UTC times as strings for the SQL query
        today_start_str = today_start_utc.strftime('%Y-%m-%d %H:%M:%S')
        # Format the end time string potentially including milliseconds if SQLite stores them
        # Let's try with seconds first, if it fails, try '%Y-%m-%d %H:%M:%S.%f'
        today_end_str = today_end_utc.strftime('%Y-%m-%d %H:%M:%S')


        # Debugging prints - keep these while testing Appointments Today
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

        # Debugging print
        print(f"  Database count for today: {stats['appointments_today']}")
        print(f"--- End Debugging ---\n")


        return jsonify(stats)

    except sqlite3.Error as e:
        print(f"Database error fetching stats: {e}")
        return jsonify({'error': 'Could not fetch system statistics', 'details': str(e)}), 500 # Internal Server Error
    except Exception as e: # Catch other potential errors like timezone issues
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
        # Fetch recent patients (last 5 by patient_id - assuming higher IDs are more recent, or add a timestamp)
        # Ordering by patient_id as a proxy for recency. For accuracy, add a 'created_at' column.
        recent_patients = cursor.execute(
            "SELECT patient_id, name FROM patients ORDER BY patient_id DESC LIMIT 5"
        ).fetchall()
        recent_data['patients'] = [dict(row) for row in recent_patients] # Convert rows to dictionaries

        # Fetch recent admissions (last 5 by admission_time)
        recent_admissions_raw = cursor.execute(
            "SELECT a.admission_id, p.name AS patient_name, a.admission_time FROM admissions a JOIN patients p ON a.patient_id = p.patient_id ORDER BY a.admission_time DESC LIMIT 5"
        ).fetchall()

        # Process admissions to convert timestamp from database (assuming UTC) to Asia/Kolkata (IST)
        recent_admissions_processed = []
        utc = pytz.timezone('UTC') # Define UTC timezone
        kolkata_tz = pytz.timezone('Asia/Kolkata') # Define India/Kolkata timezone (IST)

        for row in recent_admissions_raw:
            admission = dict(row)
            raw_admission_time_str = admission['admission_time']

            # Try parsing with and without microseconds to be robust
            try:
                # Assuming format 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD HH:MM:SS.f'
                if '.' in raw_admission_time_str:
                     admission_time_utc_naive = datetime.strptime(raw_admission_time_str, '%Y-%m-%d %H:%M:%S.%f')
                else:
                    admission_time_utc_naive = datetime.strptime(raw_admission_time_str, '%Y-%m-%d %H:%M:%S')

                # Make the datetime object timezone-aware (assuming the database stores UTC)
                admission_time_utc_aware = utc.localize(admission_time_utc_naive)

                # Convert from UTC to Asia/Kolkata (IST)
                admission_time_kolkata = admission_time_utc_aware.astimezone(kolkata_tz)

                # Format the time in the desired string format for the frontend
                # Example format: 'Apr 20, 2025 08:16 PM IST'
                # Using a format that explicitly includes the timezone abbreviation
                formatted_admission_time = admission_time_kolkata.strftime('%b %d, %Y %I:%M %p %Z')

                # Replace the raw timestamp with the formatted string
                admission['admission_time'] = formatted_admission_time

            except (ValueError, TypeError) as e:
                 print(f"Error parsing or converting admission time '{raw_admission_time_str}': {e}")
                 admission['admission_time'] = 'Invalid Time' # Handle cases where timestamp format is unexpected

            recent_admissions_processed.append(admission)

        recent_data['admissions'] = recent_admissions_processed


        return jsonify(recent_data)

    except sqlite3.Error as e:
        print(f"Database error fetching recent activities: {e}")
        return jsonify({'error': 'Could not fetch recent activities', 'details': str(e)}), 500
    except Exception as e: # Catch other potential errors like timezone issues from pytz
        print(f"General error fetching recent activities: {e}")
        return jsonify({'error': 'Could not fetch recent activities', 'details': str(e)}), 500

    finally:
        close_db(conn)

# === END NEW ENDPOINTS ===

# Add this new route to your app.py

@app.route('/get_now_serving', methods=['GET'])
def get_now_serving():
    conn = get_db()
    cursor = conn.cursor()
    serving_data = []

    try:
        # Query to find entries with status 'Serving' and get department and token number
        # If a department can have multiple serving tokens, this query might need refinement
        # This query assumes at most one 'Serving' token per department for display purposes
        serving_tokens = cursor.execute(
            "SELECT department, token_number FROM opd_queue WHERE status = 'Serving' ORDER BY department, token_number"
        ).fetchall()

        # Convert rows to a list of dictionaries
        serving_data = [dict(row) for row in serving_tokens]

        return jsonify(serving_data)

    except sqlite3.Error as e:
        print(f"Database error fetching now serving data: {e}")
        return jsonify({'error': 'Could not fetch now serving data', 'details': str(e)}), 500

    finally:
        close_db(conn)

# Add this new route to your app.py

@app.route('/get_admissions_data', methods=['GET']) # Renamed route for clarity (optional)
def get_admissions_data():
    conn = None # Initialize conn to None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # 1. Determine the date range for the last 5 days
        today = datetime.now().date()
        last_5_days_dates = [(today - timedelta(days=i)) for i in range(4, -1, -1)] # List of date objects [4 days ago, ..., today]
        date_strings = [d.strftime('%Y-%m-%d') for d in last_5_days_dates] # List of 'YYYY-MM-DD' strings
        start_date_str = date_strings[0] # The date 4 days ago

        # 2. Query admissions grouped by date for the last 5 days
        # Use DATE() function for SQLite to extract date part
        # Filter records from the start date onwards
        query = """
            SELECT
                DATE(admission_time) AS admission_date,
                COUNT(*) AS daily_admissions_count
            FROM
                admissions
            WHERE
                DATE(admission_time) >= ?
            GROUP BY
                admission_date
            ORDER BY
                admission_date ASC;
        """
        # Execute query safely with parameter binding
        cursor.execute(query, (start_date_str,))
        admissions_from_db = cursor.fetchall()

        # 3. Create a dictionary to easily lookup counts by date
        db_counts = {row['admission_date']: row['daily_admissions_count'] for row in admissions_from_db}

        # 4. Prepare final data ensuring all 5 days are present (with 0 count if no admissions)
        final_admissions_data = {'labels': [], 'data': []}
        for date_str in date_strings:
            final_admissions_data['labels'].append(date_str) # Use 'YYYY-MM-DD' as label
            # Get count from db_counts, default to 0 if date not found
            final_admissions_data['data'].append(db_counts.get(date_str, 0))

        return jsonify(final_admissions_data)

    except sqlite3.Error as e:
        print(f"Database error fetching daily admissions data: {e}")
        # Ensure consistent error format
        return jsonify({'error': True, 'message': 'Could not fetch daily admissions data', 'details': str(e)}), 500
    except Exception as e:
        print(f"General error fetching daily admissions data: {e}")
         # Ensure consistent error format
        return jsonify({'error': True, 'message': 'An unexpected error occurred', 'details': str(e)}), 500
    finally:
        # Ensure close_db is called even if conn wasn't successfully assigned in try block
        if conn:
            close_db(conn)

# --- Chatbot Endpoint (Gemini Integration with Serializable History and Commands) ---
@app.route('/chatbot/send_message', methods=['POST'])
def chatbot_send_message():
    """
    Receives message, checks for commands, gets data from DB if needed,
    manages history, and uses Gemini for general queries.
    """
    # Check if the Gemini model was successfully initialized (still needed for general queries)
    # We check this here so commands can still work even if Gemini is offline,
    # but general questions will return an error.
    gemini_available = model is not None


    if request.method == 'POST':
        try:
            data = request.get_json()
            user_message_text = data.get('message')

            if not user_message_text:
                return jsonify({'response': 'Error: No message received.'}), 400 # Bad Request

            print(f"Received message: {user_message_text}")

            # --- Manage Conversation History in Session ---
            # Retrieve serializable history from the session
            serializable_history = session.get('chat_history', [])

            # Append the new user message text to the serializable history *before* command check.
            # This way, the command is part of the history passed to Gemini if it's not handled internally,
            # and it's also stored correctly if a command IS handled internally.
            serializable_history.append({'role': 'user', 'parts': [{'text': user_message_text}]})
            # --- End Manage Conversation History ---


            # --- Command Handling Logic ---
            # Initialize bot_response_text to None. It will be set if a command is matched and processed.
            bot_response_text = None
            command_handled = False # Flag to indicate if a command was processed

            user_message_lower = user_message_text.lower()

            try:
                 # Get database connection here, *before* command checks that might need it.
                 db = get_db()

                 # --- Add your specific command checks here ---

                 if "total patients" in user_message_lower or "number of patients" in user_message_lower:
                     print("Recognized command: total patients")
                     try:
                         # Securely query your database using get_db()
                         # !!! IMPORTANT: Adjust table and column names to match your schema !!!
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
                         command_handled = True # Still consider it handled, even if failed

                 elif "available beds" in user_message_lower or "free beds" in user_message_lower:
                     print("Recognized command: available beds")
                     try:
                         # Assuming you have a way to calculate available beds (e.g., beds - occupied)
                         # Replace with your actual database query for available beds
                         # !!! IMPORTANT: Adjust table and column names to match your schema !!!
                         available_beds_row = db.execute('SELECT COUNT(*) FROM beds WHERE status = "available"').fetchone() # Example query
                         available_beds = available_beds_row[0] if available_beds_row else 0
                         bot_response_text = f"There are currently {available_beds} available beds."
                         command_handled = True
                         print(f"Handled command: available beds, response: {bot_response_text}")
                     except Exception as db_error:
                         print(f"Database error fetching available beds: {db_error}")
                         import traceback
                         traceback.print_exc()
                         bot_response_text = "Sorry, I couldn't retrieve the available bed count right now due to a database error."
                         command_handled = True # Still consider it handled, even if failed

                 # Add more elif blocks here for other specific commands you want to handle internally
                 # Remember to use db = get_db() to interact with your database securely.
                 # Ensure sensitive data (like patient names, details) is NOT included in the response text
                 # if it's not appropriate for a general chatbot interface.
                 # elif "recent admissions" in user_message_lower:
                 #     print("Recognized command: recent admissions")
                 #     try:
                 #         # Logic to fetch recent admissions from DB
                 #         # ... get data from db ...
                 #         bot_response_text = "Here are the recent admissions..." # Generate response from DB data
                 #         command_handled = True
                 #     except Exception as db_error:
                 #          print(f"Database error fetching recent admissions: {db_error}")
                 #          import traceback
                 #          traceback.print_exc()
                 #          bot_response_text = "Sorry, I couldn't retrieve recent admissions right now."
                 #          command_handled = True


            except Exception as command_error:
                # Catch errors specifically within your command handling logic
                print(f"Error during command handling logic execution: {command_error}")
                import traceback
                traceback.print_exc()
                # Set a fallback message if an unexpected error occurs during command processing
                bot_response_text = "An internal error occurred while trying to process your command."
                command_handled = True # Treat as handled to avoid hitting Gemini fallback


            # --- End Command Handling Logic ---

            # --- Gemini API Logic (Fallback for Unrecognized Commands or General Queries) ---
            # Only call Gemini if no specific command was handled internally (command_handled is still False)
            if not command_handled:
                 print("No command handled internally, sending to Gemini API...")
                 if not gemini_available:
                     # If Gemini model is not available and no internal command was handled
                     bot_response_text = "Error: Chatbot service is currently unavailable."
                 else:
                     try:
                         # Use the chat session with the history that includes the user's current message.
                         # The Gemini model's system_instruction will still apply here,
                         # which helps in guiding its response for general questions.
                         chat = model.start_chat(history=serializable_history)
                         response = chat.send_message(user_message_text) # Send only the latest message text

                         if response and hasattr(response, 'text'):
                             bot_response_text = response.text
                             print("Response generated by Gemini.")
                         else:
                              print(f"Gemini API returned unexpected response structure: {response}")
                              import json
                              try:
                                  print(f"Gemini response object (attempted JSON): {json.dumps(response, default=str)}") # Use default=str for unserializable objects
                              except TypeError:
                                   print(f"Gemini response object (raw): {response}")
                              bot_response_text = "Error: Could not get a valid response from the AI."

                     except Exception as api_error:
                         print(f"Error calling Gemini API for general query: {api_error}")
                         import traceback
                         traceback.print_exc()
                         bot_response_text = "Error: Could not get a response from the AI."
                         # If API call fails, we should not update history with a potential bad response from AI


            # --- End Gemini API Logic ---

            # --- Update Serializable History with Bot Response ---
            # We append the bot's response text to the serializable history
            # This happens whether the response came from command handling or Gemini
            # Only append if bot_response_text was successfully generated (not None or initial error message)
            # Check if bot_response_text was set by either command logic or Gemini
            # If it's still the initial error message from command failure, we might not want to add it?
            # Let's add it unless it's explicitly None from a path that didn't set it.
            if bot_response_text is not None:
                 # Ensure we don't append the same error message twice if it was set earlier
                 # A simpler approach is just to append whatever bot_response_text is at the end
                 serializable_history.append({'role': 'model', 'parts': [{'text': bot_response_text}]})
                 # Save the updated serializable history back to the session
                 session['chat_history'] = serializable_history
                 # Print history for debugging (optional)
                 # print("Current Conversation History in Session:", session.get('chat_history', []))


            # --- Return Response ---
            # Ensure bot_response_text has a value before returning
            if bot_response_text is None:
                 # Fallback if somehow no response was generated (shouldn't happen with current logic)
                 bot_response_text = "Sorry, I didn't understand that or encountered an issue."
                 # In this rare case, maybe don't add to history? Or add with a special marker?
                 # For simplicity, we'll return it.

            return jsonify({'response': bot_response_text}), 200 # Always return 200 if we reached here and have a response


        except Exception as e:
            # Catch broader errors in the request handling process (e.g., issues with request.get_json, initial session retrieval)
            print(f"Fatal error in chatbot_send_message: {e}")
            import traceback
            traceback.print_exc()
            # Clear history on fatal errors to potentially allow a clean restart on next interaction
            session.pop('chat_history', None)
            # Return a server error response to the frontend
            return jsonify({'response': 'Error: An unexpected error occurred on the server.'}), 500 # Internal Server Error

    # Handle cases where the request method is not POST
    return jsonify({'response': 'Error: Method not allowed.'}), 405 # Method Not Allowed

# --- End Chatbot Endpoint ---

if __name__ == '__main__':
    app.run(debug=True)

# flask --app app.py --debug run