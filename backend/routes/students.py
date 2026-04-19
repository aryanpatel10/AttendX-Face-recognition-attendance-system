import os
import base64
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash
from backend.database import get_db
from backend.ml.face_engine import enroll_from_images, encode_embedding

students_bp = Blueprint('students', __name__)

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'photos')
os.makedirs(PHOTOS_DIR, exist_ok=True)


@students_bp.route('/', methods=['GET'])
@jwt_required()
def list_students():
    department = request.args.get('department')
    semester = request.args.get('semester')

    query = '''
        SELECT s.*, u.full_name, u.email
        FROM students s JOIN users u ON s.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if department:
        query += ' AND s.department = ?'
        params.append(department)
    if semester:
        query += ' AND s.semester = ?'
        params.append(int(semester))

    db = get_db()
    rows = db.execute(query, params).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@students_bp.route('/<student_id>', methods=['GET'])
@jwt_required()
def get_student(student_id):
    db = get_db()
    student = db.execute(
        'SELECT s.*, u.full_name, u.email FROM students s JOIN users u ON s.user_id = u.id WHERE s.student_id = ?',
        (student_id,)
    ).fetchone()
    if not student:
        db.close()
        return jsonify({'error': 'Not found'}), 404

    total = db.execute('SELECT COUNT(*) FROM attendance WHERE student_id = ?', (student['id'],)).fetchone()[0]
    present = db.execute(
        "SELECT COUNT(*) FROM attendance WHERE student_id = ? AND status = 'present'", (student['id'],)
    ).fetchone()[0]
    db.close()

    result = dict(student)
    result['face_embedding'] = None  # Don't expose embedding
    result['attendance_stats'] = {
        'total': total,
        'present': present,
        'percentage': round(present / total * 100, 1) if total else 0
    }
    return jsonify(result)


@students_bp.route('/create', methods=['POST'])
@jwt_required()
def create_student():
    data = request.get_json()
    required = ['email', 'password', 'full_name', 'student_id', 'roll_number', 'department', 'semester']
    for f in required:
        if not data.get(f):
            return jsonify({'error': f'{f} is required'}), 400

    db = get_db()
    # Check duplicates
    if db.execute('SELECT id FROM users WHERE email = ?', (data['email'],)).fetchone():
        db.close()
        return jsonify({'error': 'Email already exists'}), 400
    if db.execute('SELECT id FROM students WHERE student_id = ?', (data['student_id'],)).fetchone():
        db.close()
        return jsonify({'error': 'Student ID already exists'}), 400

    hashed = generate_password_hash(data['password'])
    cur = db.execute(
        'INSERT INTO users (email, password, full_name, role) VALUES (?, ?, ?, ?)',
        (data['email'], hashed, data['full_name'], 'student')
    )
    user_id = cur.lastrowid

    db.execute(
        '''INSERT INTO students (user_id, student_id, roll_number, department, semester, phone)
           VALUES (?, ?, ?, ?, ?, ?)''',
        (user_id, data['student_id'], data['roll_number'],
         data['department'], data['semester'], data.get('phone', ''))
    )
    db.commit()
    db.close()
    return jsonify({'message': 'Student created', 'student_id': data['student_id']}), 201


@students_bp.route('/enroll-face', methods=['POST'])
@jwt_required()
def enroll_face():
    data = request.get_json()
    student_id = data.get('student_id')
    images = data.get('images', [])   # list of base64 strings

    if not student_id or not images:
        return jsonify({'error': 'student_id and images required'}), 400
    if len(images) < 5:
        return jsonify({'error': 'At least 5 images required for enrollment'}), 400

    db = get_db()
    student = db.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    if not student:
        db.close()
        return jsonify({'error': 'Student not found'}), 404

    embedding, count = enroll_from_images(images)
    if embedding is None:
        db.close()
        return jsonify({'error': 'No face detected in images. Use clear, well-lit frontal photos.'}), 422

    # Save first image as profile photo
    photo_path = None
    try:
        raw_b64 = images[0].split(',', 1)[-1]
        photo_bytes = base64.b64decode(raw_b64)
        photo_filename = f'{student_id}.jpg'
        photo_path = os.path.join(PHOTOS_DIR, photo_filename)
        with open(photo_path, 'wb') as f:
            f.write(photo_bytes)
        photo_path = f'photos/{photo_filename}'
    except Exception:
        pass

    emb_str = encode_embedding(embedding)
    db.execute(
        '''UPDATE students
           SET face_embedding = ?, face_enrolled = 1, enrollment_img_count = ?, photo_path = ?
           WHERE student_id = ?''',
        (emb_str, count, photo_path, student_id)
    )
    db.commit()
    db.close()

    return jsonify({'message': 'Face enrolled successfully', 'images_used': count})
