-- schema.sql

-- Drop existing tables
DROP TABLE IF EXISTS patient_profiles;
DROP TABLE IF EXISTS doctor_profiles;
DROP TABLE IF EXISTS hospital_profiles;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS inventory;
DROP TABLE IF EXISTS opd_queue;
DROP TABLE IF EXISTS beds;
DROP TABLE IF EXISTS admissions;
DROP TABLE IF EXISTS patients;

-- Patients table
CREATE TABLE patients (
    patient_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    contact_number TEXT,
    address TEXT,
    emergency_contact TEXT,
    blood_group TEXT,
    medical_history TEXT
);

-- OPD queue table
CREATE TABLE opd_queue (
    queue_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    department TEXT NOT NULL,
    token_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Waiting',
    check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- Beds table
CREATE TABLE beds (
    bed_id TEXT PRIMARY KEY,
    ward TEXT NOT NULL,
    bed_number TEXT NOT NULL,
    bed_type TEXT,
    status TEXT NOT NULL DEFAULT 'Available',
    current_patient_id TEXT,
    FOREIGN KEY (current_patient_id) REFERENCES patients(patient_id)
);

-- Admissions table
CREATE TABLE admissions (
    admission_id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL,
    bed_id TEXT NOT NULL,
    admission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'Admitted',
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (bed_id) REFERENCES beds(bed_id)
);

-- Inventory table
CREATE TABLE inventory (
    item_id TEXT PRIMARY KEY,
    item_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    unit TEXT
);

-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    user_type TEXT NOT NULL
);

-- Profile tables for role‑specific data
CREATE TABLE hospital_profiles (
    user_id INTEGER PRIMARY KEY,
    hospital_name TEXT NOT NULL,
    location TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE doctor_profiles (
    user_id INTEGER PRIMARY KEY,
    specialization TEXT NOT NULL,
    experience INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE patient_profiles (
    user_id INTEGER PRIMARY KEY,
    
    age INTEGER,
    gender TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- git status
-- git add .
-- git commit -m "Improved inventory UI and fixed duplicate doctor cards"
-- git push origin main

-- Initialize database via Flask CLI
-- flask --app app.py initdb