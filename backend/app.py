from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import uuid
from datetime import datetime
import os
from dotenv import load_dotenv

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
    protected_routes = ['list_admissions', 'add_inventory_item', 'add_bed']
    if 'user_id' not in session and request.endpoint in protected_routes:
        return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Base user data
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm  = request.form.get('confirm_password')

        # Additional common info
        name  = request.form.get('name')
        phone = request.form.get('phone')

        # Role-specific extra details
        extra = {}
        if user_type == 'hospital':
            extra['hospital_name'] = request.form.get('hospital_name')
            extra['location']      = request.form.get('location')
        elif user_type == 'doctor':
            extra['specialization'] = request.form.get('specialization')
            extra['experience']     = request.form.get('experience')
        elif user_type == 'patient':
            extra['age']    = request.form.get('age')
            extra['gender'] = request.form.get('gender')

        # Validate
        error = None
        if not user_type:
            error = 'User type is required.'
        elif not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm:
            error = 'Passwords do not match.'

        conn = get_db()
        cursor = conn.cursor()
        # Check existing
        if not error:
            existing = cursor.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
            if existing:
                error = 'Email already registered.'

        if error:
            flash(error, 'danger')
            close_db(conn)
            return render_template('register.html')

        # Create user
        try:
            pwd_hash = generate_password_hash(password)
            cursor.execute(
                'INSERT INTO users (email, password_hash, user_type) VALUES (?,?,?)',
                (email, pwd_hash, user_type)
            )
            conn.commit()
            user_id = cursor.lastrowid
            # Insert into profile
            if user_type == 'hospital':
                cursor.execute(
                    'INSERT INTO hospital_profiles (user_id,hospital_name,location) VALUES (?,?,?)',
                    (user_id, extra['hospital_name'], extra['location'])
                )
            elif user_type == 'doctor':
                cursor.execute(
                    'INSERT INTO doctor_profiles (user_id,specialization,experience) VALUES (?,?,?)',
                    (user_id, extra['specialization'], extra['experience'])
                )
            elif user_type == 'patient':
                cursor.execute(
                    'INSERT INTO patient_profiles (user_id,age,gender) VALUES (?,?,?)',
                    (user_id, extra['age'], extra['gender'])
                )
            conn.commit()
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.Error as e:
            flash(f'Database error: {e}', 'danger')
        finally:
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
    return redirect(url_for('login'))

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
    patients = conn.execute("SELECT patient_id, name FROM patients").fetchall()
    close_db(conn)

    if request.method == 'POST':
        patient_id = request.form['patient_id']
        department = request.form['department']
        queue_id = str(uuid.uuid4())

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(token_number) FROM opd_queue WHERE department = ?", (department,))
        result = cursor.fetchone()[0]
        next_token = (result + 1) if result is not None else 1

        try:
            cursor.execute("INSERT INTO opd_queue (queue_id, patient_id, department, token_number) VALUES (?, ?, ?, ?)",
                           (queue_id, patient_id, department, next_token))
            conn.commit()
        except sqlite3.Error as e:
            flash(f"Error joining queue: {e}", "danger")
        finally:
            close_db(conn)
        return redirect(url_for('view_opd_queue'))
    return render_template('join_opd_queue.html', patients=patients)

@app.route('/opd/queue')
def view_opd_queue():
    conn = get_db()
    queue_entries = conn.execute("""
        SELECT q.token_number, p.name, q.department, q.status, q.check_in_time
        FROM opd_queue q
        JOIN patients p ON q.patient_id = p.patient_id
        ORDER BY q.token_number
    """).fetchall()
    close_db(conn)
    return render_template('view_opd_queue.html', queue=queue_entries)

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

if __name__ == '__main__':
    app.run(debug=True)

# flask --app app.py --debug run