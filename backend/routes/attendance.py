from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.database import get_db
from backend.ml.face_engine import recognize_frame

attendance_bp = Blueprint('attendance', __name__)


# ── Sessions ──────────────────────────────────────────────────────────────────

@attendance_bp.route('/sessions/start', methods=['POST'])
@jwt_required()
def start_session():
    data = request.get_json()
    subject_id = data.get('subject_id')
    notes = data.get('notes', '')
    if not subject_id:
        return jsonify({'error': 'subject_id required'}), 400

    user_id = int(get_jwt_identity())
    now = datetime.now()
    db = get_db()

    cur = db.execute(
        'INSERT INTO attendance_sessions (subject_id, teacher_id, date, start_time, notes) VALUES (?, ?, ?, ?, ?)',
        (subject_id, user_id, now.strftime('%Y-%m-%d'), now.strftime('%H:%M:%S'), notes)
    )
    session_id = cur.lastrowid

    # Pre-populate absent records for all enrolled students
    enrolled = db.execute(
        'SELECT student_id FROM subject_enrollments WHERE subject_id = ?', (subject_id,)
    ).fetchall()

    for e in enrolled:
        db.execute(
            'INSERT OR IGNORE INTO attendance (session_id, student_id, subject_id, status) VALUES (?, ?, ?, ?)',
            (session_id, e['student_id'], subject_id, 'absent')
        )

    db.commit()
    db.close()
    return jsonify({'session_id': session_id, 'message': 'Session started'})


@attendance_bp.route('/sessions/<int:session_id>/end', methods=['POST'])
@jwt_required()
def end_session(session_id):
    db = get_db()
    now = datetime.now().strftime('%H:%M:%S')
    db.execute(
        'UPDATE attendance_sessions SET is_active = 0, end_time = ? WHERE id = ?',
        (now, session_id)
    )
    db.commit()
    db.close()
    return jsonify({'message': 'Session ended'})


@attendance_bp.route('/sessions/<int:session_id>/summary', methods=['GET'])
@jwt_required()
def session_summary(session_id):
    db = get_db()
    session = db.execute('SELECT * FROM attendance_sessions WHERE id = ?', (session_id,)).fetchone()
    if not session:
        db.close()
        return jsonify({'error': 'Session not found'}), 404

    records = db.execute(
        '''SELECT a.*, s.student_id, u.full_name
           FROM attendance a
           JOIN students s ON a.student_id = s.id
           JOIN users u ON s.user_id = u.id
           WHERE a.session_id = ?''',
        (session_id,)
    ).fetchall()
    db.close()

    present = [dict(r) for r in records if r['status'] == 'present']
    absent  = [dict(r) for r in records if r['status'] != 'present']
    total   = len(records)

    return jsonify({
        'session_id': session_id,
        'date': session['date'],
        'is_active': bool(session['is_active']),
        'total': total,
        'present_count': len(present),
        'absent_count': len(absent),
        'percentage': round(len(present) / total * 100, 1) if total else 0,
        'present': present,
        'absent': absent,
    })


@attendance_bp.route('/sessions', methods=['GET'])
@jwt_required()
def list_sessions():
    db = get_db()
    rows = db.execute(
        '''SELECT s.*, sub.name as subject_name, sub.code as subject_code, u.full_name as teacher_name
           FROM attendance_sessions s
           JOIN subjects sub ON s.subject_id = sub.id
           JOIN users u ON s.teacher_id = u.id
           ORDER BY s.created_at DESC LIMIT 50'''
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


# ── Face Recognition ──────────────────────────────────────────────────────────

@attendance_bp.route('/recognize', methods=['POST'])
@jwt_required()
def recognize():
    data = request.get_json()
    frame_b64 = data.get('frame')
    session_id = data.get('session_id')

    if not frame_b64 or not session_id:
        return jsonify({'error': 'frame and session_id required'}), 400

    db = get_db()

    # Get session to find subject_id
    session = db.execute(
        'SELECT * FROM attendance_sessions WHERE id = ?', (session_id,)
    ).fetchone()
    if not session:
        db.close()
        return jsonify({'error': 'Session not found'}), 404

    # Load all enrolled students with embeddings
    enrolled = db.execute(
        '''SELECT s.id as db_id, s.student_id, u.full_name as name, s.face_embedding as embedding_str
           FROM students s
           JOIN users u ON s.user_id = u.id
           WHERE s.face_enrolled = 1 AND s.face_embedding IS NOT NULL'''
    ).fetchall()

    enrolled_list = [dict(r) for r in enrolled]

    # Already-marked students for this session
    marked = db.execute(
        "SELECT student_id FROM attendance WHERE session_id = ? AND status = 'present'",
        (session_id,)
    ).fetchall()
    marked_ids = {r['student_id'] for r in marked}

    # Run recognition
    results = recognize_frame(frame_b64, enrolled_list)

    # Mark attendance for recognized students
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
    for r in results:
        if r['recognized'] and r['match']:
            db_id = r['match']['db_id']
            if db_id not in marked_ids:
                # Upsert: update existing absent record or insert new present record
                existing = db.execute(
                    'SELECT id FROM attendance WHERE session_id = ? AND student_id = ?',
                    (session_id, db_id)
                ).fetchone()
                if existing:
                    db.execute(
                        '''UPDATE attendance
                           SET status = 'present', recognition_confidence = ?, marked_at = ?, marked_by_face = 1
                           WHERE id = ?''',
                        (r['match']['confidence'], now_str, existing['id'])
                    )
                else:
                    db.execute(
                        '''INSERT INTO attendance (session_id, student_id, subject_id, status,
                           recognition_confidence, marked_at, marked_by_face)
                           VALUES (?, ?, ?, 'present', ?, ?, 1)''',
                        (session_id, db_id, session['subject_id'], r['match']['confidence'], now_str)
                    )
                marked_ids.add(db_id)
                r['just_marked'] = True
            else:
                r['just_marked'] = False

    db.commit()
    db.close()
    return jsonify({'results': results})


# ── Manual mark ───────────────────────────────────────────────────────────────

@attendance_bp.route('/manual-mark', methods=['POST'])
@jwt_required()
def manual_mark():
    data = request.get_json()
    session_id = data.get('session_id')
    student_id_str = data.get('student_id')
    status = data.get('status', 'present')

    db = get_db()
    student = db.execute('SELECT id FROM students WHERE student_id = ?', (student_id_str,)).fetchone()
    if not student:
        db.close()
        return jsonify({'error': 'Student not found'}), 404

    existing = db.execute(
        'SELECT id FROM attendance WHERE session_id = ? AND student_id = ?',
        (session_id, student['id'])
    ).fetchone()
    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')

    if existing:
        db.execute(
            "UPDATE attendance SET status = ?, marked_at = ?, marked_by_face = 0 WHERE id = ?",
            (status, now_str, existing['id'])
        )
    else:
        session = db.execute('SELECT subject_id FROM attendance_sessions WHERE id = ?', (session_id,)).fetchone()
        db.execute(
            'INSERT INTO attendance (session_id, student_id, subject_id, status, marked_at) VALUES (?, ?, ?, ?, ?)',
            (session_id, student['id'], session['subject_id'], status, now_str)
        )

    db.commit()
    db.close()
    return jsonify({'message': f'Marked {status}'})


# ── Reports ───────────────────────────────────────────────────────────────────

@attendance_bp.route('/report', methods=['GET'])
@jwt_required()
def report():
    subject_id  = request.args.get('subject_id')
    student_sid = request.args.get('student_id')
    from_date   = request.args.get('from_date')
    to_date     = request.args.get('to_date')

    query = '''
        SELECT a.id, a.status, a.recognition_confidence, a.marked_by_face,
               ase.date, ase.subject_id,
               s.student_id, u.full_name as student_name,
               sub.code as subject_code, sub.name as subject_name
        FROM attendance a
        JOIN attendance_sessions ase ON a.session_id = ase.id
        JOIN students s ON a.student_id = s.id
        JOIN users u ON s.user_id = u.id
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE 1=1
    '''
    params = []
    if subject_id:
        query += ' AND a.subject_id = ?'; params.append(subject_id)
    if student_sid:
        query += ' AND s.student_id = ?'; params.append(student_sid)
    if from_date:
        query += ' AND ase.date >= ?'; params.append(from_date)
    if to_date:
        query += ' AND ase.date <= ?'; params.append(to_date)
    query += ' ORDER BY ase.date DESC LIMIT 500'

    db = get_db()
    rows = db.execute(query, params).fetchall()
    db.close()
    return jsonify({'records': [dict(r) for r in rows], 'total': len(rows)})


@attendance_bp.route('/student-stats/<student_sid>', methods=['GET'])
@jwt_required()
def student_stats(student_sid):
    db = get_db()
    student = db.execute('SELECT id FROM students WHERE student_id = ?', (student_sid,)).fetchone()
    if not student:
        db.close()
        return jsonify({'error': 'Not found'}), 404

    rows = db.execute(
        '''SELECT sub.code, sub.name,
                  COUNT(a.id) as total,
                  SUM(CASE WHEN a.status='present' THEN 1 ELSE 0 END) as present
           FROM attendance a
           JOIN subjects sub ON a.subject_id = sub.id
           WHERE a.student_id = ?
           GROUP BY sub.id''',
        (student['id'],)
    ).fetchall()
    db.close()

    subjects = []
    for r in rows:
        total = r['total'] or 0
        present = r['present'] or 0
        subjects.append({
            'code': r['code'],
            'name': r['name'],
            'total': total,
            'present': present,
            'percentage': round(present / total * 100, 1) if total else 0
        })
    return jsonify({'student_id': student_sid, 'subjects': subjects})
