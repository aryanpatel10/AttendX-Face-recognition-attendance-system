import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'attendance.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT UNIQUE NOT NULL,
            password    TEXT NOT NULL,
            full_name   TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'student',
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS students (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id               INTEGER UNIQUE NOT NULL REFERENCES users(id),
            student_id            TEXT UNIQUE NOT NULL,
            roll_number           TEXT NOT NULL,
            department            TEXT NOT NULL,
            semester              INTEGER NOT NULL,
            phone                 TEXT,
            photo_path            TEXT,
            face_enrolled         INTEGER DEFAULT 0,
            enrollment_img_count  INTEGER DEFAULT 0,
            face_embedding        TEXT,
            created_at            TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            department  TEXT NOT NULL,
            semester    INTEGER NOT NULL,
            credits     INTEGER DEFAULT 3,
            teacher_id  INTEGER REFERENCES users(id),
            is_active   INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subject_enrollments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id  INTEGER NOT NULL REFERENCES students(id),
            subject_id  INTEGER NOT NULL REFERENCES subjects(id),
            UNIQUE(student_id, subject_id)
        );

        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id  INTEGER NOT NULL REFERENCES subjects(id),
            teacher_id  INTEGER NOT NULL REFERENCES users(id),
            date        TEXT NOT NULL,
            start_time  TEXT NOT NULL,
            end_time    TEXT,
            is_active   INTEGER DEFAULT 1,
            notes       TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id             INTEGER NOT NULL REFERENCES attendance_sessions(id),
            student_id             INTEGER NOT NULL REFERENCES students(id),
            subject_id             INTEGER NOT NULL REFERENCES subjects(id),
            status                 TEXT DEFAULT 'absent',
            recognition_confidence REAL,
            marked_at              TEXT,
            marked_by_face         INTEGER DEFAULT 0,
            notes                  TEXT,
            created_at             TEXT DEFAULT (datetime('now')),
            UNIQUE(session_id, student_id)
        );
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized at:", os.path.abspath(DB_PATH))
