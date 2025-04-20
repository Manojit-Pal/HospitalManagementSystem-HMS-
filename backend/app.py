from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import uuid
import os
from dotenv import load_dotenv
from flask import jsonify # Make sure jsonify is imported at the top
from datetime import datetime, date # Make sure datetime and date are imported
import pytz

load_dotenv()  # Load environment variables from .env
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
        'dashboard', # <--- Add the endpoint name for your dashboard page here
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

@app.route('/get_admissions_data', methods=['GET'])
def get_admissions_data():
    conn = get_db()
    cursor = conn.cursor()
    admissions_data = {'labels': [], 'data': []}

    try:
        # Query to count admissions by month (YYYY-MM)
        # strftime('%Y-%m', admission_time) extracts the year and month
        # GROUP BY combines rows with the same year and month
        # ORDER BY ensures the months are in chronological order
        admissions_by_month = cursor.execute(
            "SELECT strftime('%Y-%m', admission_time) AS admission_month, COUNT(*) AS admission_count FROM admissions GROUP BY admission_month ORDER BY admission_month"
        ).fetchall()

        # Prepare data for Chart.js
        for row in admissions_by_month:
            # Format the month label (e.g., "2025-01" -> "Jan 2025")
            month_str = row['admission_month']
            # Parse the YYYY-MM string into a datetime object
            date_obj = datetime.strptime(month_str, '%Y-%m')
            # Format into a more readable string like "Jan 2025"
            formatted_month = date_obj.strftime('%b %Y')

            admissions_data['labels'].append(formatted_month)
            admissions_data['data'].append(row['admission_count'])

        return jsonify(admissions_data)

    except sqlite3.Error as e:
        print(f"Database error fetching admissions data: {e}")
        return jsonify({'error': 'Could not fetch admissions data', 'details': str(e)}), 500
    except Exception as e:
        print(f"General error fetching admissions data: {e}")
        return jsonify({'error': 'Could not fetch admissions data', 'details': str(e)}), 500

    finally:
        close_db(conn)

if __name__ == '__main__':
    app.run(debug=True)

# flask --app app.py --debug run