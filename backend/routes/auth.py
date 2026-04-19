from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import get_db

auth_bp = Blueprint('auth', __name__)
HASH_METHOD = 'pbkdf2:sha256'

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email     = data.get('email', '').strip()
    password  = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role      = data.get('role', 'student')

    if not email or not password or not full_name:
        return jsonify({'error': 'email, password and full_name are required'}), 400
    if role not in ('admin', 'teacher', 'student'):
        return jsonify({'error': 'Invalid role'}), 400

    db = get_db()
    if db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
        db.close()
        return jsonify({'error': 'Email already registered'}), 400

    hashed = generate_password_hash(password, method=HASH_METHOD)
    cur = db.execute(
        'INSERT INTO users (email, password, full_name, role) VALUES (?, ?, ?, ?)',
        (email, hashed, full_name, role)
    )
    db.commit()
    user_id = cur.lastrowid
    db.close()

    token = create_access_token(identity=str(user_id))
    return jsonify({
        'access_token': token,
        'user': {'id': user_id, 'email': email, 'full_name': full_name, 'role': role}
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    db   = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    db.close()

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid email or password'}), 401
    if not user['is_active']:
        return jsonify({'error': 'Account is deactivated'}), 403

    token = create_access_token(identity=str(user['id']))
    return jsonify({
        'access_token': token,
        'user': {
            'id':        user['id'],
            'email':     user['email'],
            'full_name': user['full_name'],
            'role':      user['role']
        }
    })

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    user_id = int(get_jwt_identity())
    db   = get_db()
    user = db.execute('SELECT id, email, full_name, role FROM users WHERE id = ?', (user_id,)).fetchone()
    db.close()
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(user))
