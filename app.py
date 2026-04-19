"""
FaceAttend — Flask Backend
Run:  python app.py
Then open: http://localhost:5000
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.database import init_db
from backend.routes.auth import auth_bp
from backend.routes.students import students_bp
from backend.routes.subjects import subjects_bp
from backend.routes.attendance import attendance_bp

BASE_DIR     = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
PHOTOS_DIR   = os.path.join(BASE_DIR, 'photos')
os.makedirs(PHOTOS_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config['JWT_SECRET_KEY']           = 'faceattend-dev-secret-2024'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False
app.config['MAX_CONTENT_LENGTH']       = 32 * 1024 * 1024

CORS(app, resources={r'/api/*': {'origins': '*'}})
JWTManager(app)

# API blueprints
app.register_blueprint(auth_bp,       url_prefix='/api/auth')
app.register_blueprint(students_bp,   url_prefix='/api/students')
app.register_blueprint(subjects_bp,   url_prefix='/api/subjects')
app.register_blueprint(attendance_bp, url_prefix='/api/attendance')

# Static assets
@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)

@app.route('/photos/<path:filename>')
def serve_photos(filename):
    return send_from_directory(PHOTOS_DIR, filename)

# Page routes — all handled by one function with unique endpoint names
PAGES = {
    '/':           'login.html',
    '/login':      'login.html',
    '/register':   'register.html',
    '/dashboard':  'dashboard.html',
    '/students':   'students.html',
    '/subjects':   'subjects.html',
    '/attendance': 'attendance.html',
    '/sessions':   'sessions.html',
    '/reports':    'reports.html',
    '/enroll':     'enroll.html',
}

@app.route('/')
@app.route('/login')
@app.route('/register')
@app.route('/dashboard')
@app.route('/students')
@app.route('/subjects')
@app.route('/attendance')
@app.route('/sessions')
@app.route('/reports')
@app.route('/enroll')
def serve_page():
    from flask import request
    path = request.path.lstrip('/')
    html_file = PAGES.get('/' + path, PAGES.get('/' + path.rstrip('/'), 'login.html'))
    return send_from_directory(os.path.join(FRONTEND_DIR, 'pages'), html_file)

@app.route('/api')
def api_index():
    return jsonify({'app': 'FaceAttend', 'version': '1.0.0', 'status': 'running'})

if __name__ == '__main__':
    print("Initialising database...")
    init_db()
    print("\n" + "="*52)
    print("  FaceAttend is running!")
    print("  Open:  http://localhost:5000")
    print("  Login: admin@demo.com  /  admin123")
    print("="*52 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
