# AttendX 🎯
### Face Recognition Attendance System

> Runs 100% on localhost · No cloud required · Python Flask + SQLite + DeepFace

---

## Overview

**AttendX** is an AI-powered attendance management system that uses real-time facial recognition to automatically mark student attendance via webcam. Teachers start a session, point the camera at the class, and AttendX does the rest — detecting faces every 2 seconds and marking students present with a confidence score.

---

## Features

- 🤖 **Live Face Recognition** — webcam scans the room every 2 seconds and marks attendance automatically
- 📸 **Face Enrollment** — capture 5+ photos per student to generate stored face embeddings
- 👨‍🎓 **Student Management** — add/manage students with department, semester, roll number, and profile photo
- 📚 **Subject Management** — create subjects, assign teachers, enroll students
- 🗓️ **Session-Based Attendance** — teachers start/end sessions per subject per class
- 📊 **Reports & CSV Export** — filter by subject, student, or date range; export to CSV
- 🔐 **JWT Authentication** — role-based access for Admin, Teacher, and Student

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask 3.0, Flask-JWT-Extended |
| Database | SQLite (local, zero config) |
| Face Recognition | DeepFace (FaceNet512) + OpenCV fallback |
| Image Processing | OpenCV, Pillow, NumPy |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Auth | JWT (JSON Web Tokens) |
| Charts | Chart.js |

---

## Project Structure

```
faceattend/
├── app.py                        ← Flask entry point (run this!)
├── seed.py                       ← Populate demo data (run once)
├── attendance.db                 ← SQLite database (auto-created)
├── photos/                       ← Student profile photos
├── requirements.txt
│
├── backend/
│   ├── database.py               ← SQLite schema & connection
│   ├── ml/
│   │   └── face_engine.py        ← Face detection, embedding & matching
│   └── routes/
│       ├── auth.py               ← /api/auth/*
│       ├── students.py           ← /api/students/*
│       ├── subjects.py           ← /api/subjects/*
│       └── attendance.py         ← /api/attendance/* + /api/attendance/recognize
│
└── frontend/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── app.js                ← API client, auth, toast, charts
    └── pages/
        ├── login.html
        ├── register.html
        ├── dashboard.html
        ├── students.html
        ├── subjects.html
        ├── attendance.html       ← Live camera + recognition
        ├── enroll.html           ← Face enrollment
        ├── sessions.html
        └── reports.html
```

---

## Setup & Installation

### Prerequisites
- Python 3.9+
- pip
- A webcam (for live recognition)
- Chrome or Firefox browser

---

### Step 1 — Clone / Download the project

```bash
cd faceattend
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `deepface` pulls in TensorFlow (~500 MB). If you want a lighter install, skip it — AttendX automatically falls back to an OpenCV-based recognizer:
> ```bash
> pip install flask flask-cors flask-jwt-extended werkzeug opencv-python-headless numpy Pillow scikit-learn
> ```

### Step 3 — Seed the demo database

```bash
python seed.py
```

This creates demo data including:
- 1 Admin account
- 1 Teacher account
- 5 Student accounts
- 4 Subjects (CS301, CS302, CS401, CS402)

### Step 4 — Run the app

```bash
python app.py
```

### Step 5 — Open in browser

```
http://localhost:5000
```

**Default login:** `admin@demo.com` / `admin123`

---

## How to Take Attendance

1. **Enroll faces** — go to *Face Enroll*, select a student, capture 5+ clear photos, click Enroll
2. **Set up subjects** — go to *Subjects*, create subjects, assign teacher, enroll students
3. **Start a session** — go to *Take Attendance*, select a subject, click **Start Session**
4. The webcam activates and scans automatically every 2 seconds
5. Recognised faces are marked **present** with a confidence score shown on screen
6. Use the manual override panel for any corrections
7. Click **End Session** when done
8. View summaries on the *Sessions* page or full reports on the *Reports* page

---

## Face Recognition Details

### With DeepFace (recommended)
- Model: **FaceNet512** — 512-dimensional face embeddings
- Detection: RetinaFace / MTCNN
- Matching: Cosine similarity (threshold: 0.55)
- Accuracy: High for frontal faces in normal lighting

### Without DeepFace (fallback)
- Detection: OpenCV Haar Cascade
- Descriptor: Flattened normalized grayscale (64×64 = 4096-dim)
- Matching: Cosine similarity
- Suitable for demos; less accurate than FaceNet in real-world conditions

### Enrollment Pipeline
5+ images per student → extract embedding from each → average all → store as JSON in SQLite

### Recognition Pipeline (per frame)
1. Detect all faces using OpenCV Haar Cascade
2. Crop each face with margin
3. Extract embedding via FaceNet512 (or fallback)
4. Compare against all stored embeddings using cosine similarity
5. If best match score > 0.55 → mark student present in DB

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login, returns JWT token |
| POST | `/api/auth/register` | Register new user |
| GET | `/api/auth/me` | Get current user info |
| GET | `/api/students/` | List all students |
| POST | `/api/students/create` | Create a student |
| POST | `/api/students/enroll-face` | Enroll face (base64 images) |
| GET | `/api/subjects/` | List all subjects |
| POST | `/api/subjects/create` | Create a subject |
| POST | `/api/subjects/enroll` | Enroll student into subject |
| POST | `/api/attendance/sessions/start` | Start an attendance session |
| POST | `/api/attendance/sessions/{id}/end` | End a session |
| GET | `/api/attendance/sessions/{id}/summary` | Get session summary |
| POST | `/api/attendance/recognize` | Recognize frame & mark attendance |
| POST | `/api/attendance/manual-mark` | Manual attendance override |
| GET | `/api/attendance/report` | Attendance report with filters |
| GET | `/api/attendance/student-stats/{id}` | Per-subject stats for a student |

---

## Troubleshooting

**Camera not working?**
- Allow camera access in your browser
- Use Chrome or Firefox (Safari may restrict webcam access)
- Access via `http://localhost:5000` (not `file://`)

**DeepFace installation failing?**
- Try: `pip install deepface --no-deps` then `pip install tensorflow numpy pillow`
- Or skip deepface entirely — the OpenCV fallback works well for demos

**Port 5000 already in use?**
- Change the port in `app.py`: `app.run(port=5001)`
- Then open `http://localhost:5001`

**Database errors?**
- Delete `attendance.db` and re-run `python seed.py`

---

## User Roles

| Role | Access |
|---|---|
| **Admin** | Full access — manage users, students, subjects, reports |
| **Teacher** | Start/end sessions, take attendance, view reports |
| **Student** | View own attendance records and stats |

