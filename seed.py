import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from werkzeug.security import generate_password_hash
from backend.database import get_db, init_db

def seed():
    init_db()
    db = get_db()

    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        print("Database already has data. Deleting and reseeding...")
        db.execute("DELETE FROM subject_enrollments")
        db.execute("DELETE FROM attendance")
        db.execute("DELETE FROM attendance_sessions")
        db.execute("DELETE FROM students")
        db.execute("DELETE FROM subjects")
        db.execute("DELETE FROM users")
        db.commit()

    method = 'pbkdf2:sha256'

    db.execute("INSERT INTO users (email, password, full_name, role) VALUES (?, ?, ?, ?)",
        ('admin@demo.com', generate_password_hash('admin123', method=method), 'System Admin', 'admin'))

    db.execute("INSERT INTO users (email, password, full_name, role) VALUES (?, ?, ?, ?)",
        ('teacher@demo.com', generate_password_hash('teacher123', method=method), 'Dr. Rajesh Sharma', 'teacher'))
    teacher_id = db.execute("SELECT id FROM users WHERE email='teacher@demo.com'").fetchone()['id']

    subjects = [
        ('CS301', 'Data Structures & Algorithms', 'Computer Science', 3, 3),
        ('CS302', 'Operating Systems',            'Computer Science', 3, 3),
        ('CS401', 'Machine Learning',             'Computer Science', 4, 4),
        ('CS402', 'Computer Networks',            'Computer Science', 3, 4),
    ]
    for code, name, dept, sem, credits in subjects:
        db.execute("INSERT INTO subjects (code, name, department, semester, credits, teacher_id) VALUES (?,?,?,?,?,?)",
            (code, name, dept, sem, credits, teacher_id))

    students = [
        ('Rahul Patel',  'rahul@demo.com',  'CS2024001', '001'),
        ('Priya Singh',  'priya@demo.com',  'CS2024002', '002'),
        ('Amit Kumar',   'amit@demo.com',   'CS2024003', '003'),
        ('Sneha Gupta',  'sneha@demo.com',  'CS2024004', '004'),
        ('Vikram Shah',  'vikram@demo.com', 'CS2024005', '005'),
    ]
    for name, email, sid, roll in students:
        db.execute("INSERT INTO users (email, password, full_name, role) VALUES (?,?,?,?)",
            (email, generate_password_hash('student123', method=method), name, 'student'))
        uid = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()['id']
        db.execute(
            "INSERT INTO students (user_id, student_id, roll_number, department, semester) VALUES (?,?,?,?,?)",
            (uid, sid, roll, 'Computer Science', 3))

    db.commit()
    db.close()
    print("Seed complete!")
    print("   Admin:   admin@demo.com   / admin123")
    print("   Teacher: teacher@demo.com / teacher123")
    print("   Student: rahul@demo.com   / student123")

if __name__ == '__main__':
    seed()
