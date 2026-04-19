from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.database import get_db

subjects_bp = Blueprint('subjects', __name__)


@subjects_bp.route('/', methods=['GET'])
@jwt_required()
def list_subjects():
    db = get_db()
    rows = db.execute('SELECT * FROM subjects WHERE is_active = 1 ORDER BY semester, code').fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@subjects_bp.route('/create', methods=['POST'])
@jwt_required()
def create_subject():
    data = request.get_json()
    for f in ['code', 'name', 'department', 'semester']:
        if not data.get(f):
            return jsonify({'error': f'{f} is required'}), 400

    db = get_db()
    if db.execute('SELECT id FROM subjects WHERE code = ?', (data['code'],)).fetchone():
        db.close()
        return jsonify({'error': 'Subject code already exists'}), 400

    user_id = int(get_jwt_identity())
    db.execute(
        'INSERT INTO subjects (code, name, department, semester, credits, teacher_id) VALUES (?, ?, ?, ?, ?, ?)',
        (data['code'], data['name'], data['department'], data['semester'], data.get('credits', 3), user_id)
    )
    db.commit()
    db.close()
    return jsonify({'message': 'Subject created'}), 201


@subjects_bp.route('/enroll', methods=['POST'])
@jwt_required()
def enroll_student():
    data = request.get_json()
    subject_id = data.get('subject_id')
    student_id = data.get('student_id')

    db = get_db()
    student = db.execute('SELECT id FROM students WHERE student_id = ?', (student_id,)).fetchone()
    if not student:
        db.close()
        return jsonify({'error': 'Student not found'}), 404

    try:
        db.execute(
            'INSERT INTO subject_enrollments (student_id, subject_id) VALUES (?, ?)',
            (student['id'], subject_id)
        )
        db.commit()
    except Exception:
        db.close()
        return jsonify({'error': 'Already enrolled'}), 400

    db.close()
    return jsonify({'message': 'Enrolled'})
