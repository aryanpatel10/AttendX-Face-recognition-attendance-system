"""
Face Recognition Engine
Uses OpenCV for face detection + DeepFace/FaceNet for embeddings.
Falls back to simple LBPH if DeepFace is unavailable.
"""
from __future__ import annotations
import base64
import io
import json
import logging
from typing import Optional
import numpy as np
import cv2
from PIL import Image

logger = logging.getLogger(__name__)

# Try importing DeepFace; fall back gracefully
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    logger.info("DeepFace loaded — using FaceNet512 embeddings")
except Exception:
    DEEPFACE_AVAILABLE = False
    logger.warning("DeepFace not available — using OpenCV LBPH fallback")


# ── Helpers ───────────────────────────────────────────────────────────────────

def decode_base64_image(b64_string: str) -> np.ndarray:
    """Decode a base64 image (with or without data-URI prefix) to BGR numpy array."""
    if ',' in b64_string:
        b64_string = b64_string.split(',', 1)[1]
    raw = base64.b64decode(b64_string)
    pil_img = Image.open(io.BytesIO(raw)).convert('RGB')
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)


def encode_embedding(embedding: np.ndarray) -> str:
    """Serialize numpy embedding to JSON string for SQLite storage."""
    return json.dumps(embedding.tolist())


def decode_embedding(embedding_str: str) -> np.ndarray:
    """Deserialize embedding from SQLite TEXT column."""
    return np.array(json.loads(embedding_str), dtype=np.float32)


def l2_normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / (norm + 1e-10)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


# ── OpenCV face detector (always available) ───────────────────────────────────

_face_cascade = None

def get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        _face_cascade = cv2.CascadeClassifier(cascade_path)
    return _face_cascade


def detect_faces_opencv(frame: np.ndarray) -> list:
    """Detect faces using OpenCV Haar cascade. Returns list of {x,y,w,h}."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    cascade = get_face_cascade()
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
    results = []
    for (x, y, w, h) in faces:
        results.append({'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)})
    return results


# ── Embedding extraction ──────────────────────────────────────────────────────

def get_embedding_deepface(face_crop: np.ndarray) -> Optional[np.ndarray]:
    """Extract 512-d FaceNet embedding via DeepFace."""
    try:
        result = DeepFace.represent(
            img_path=face_crop,
            model_name='Facenet512',
            detector_backend='skip',   # We already detected; skip re-detection
            enforce_detection=False,
            align=True,
        )
        if result:
            emb = np.array(result[0]['embedding'], dtype=np.float32)
            return l2_normalize(emb)
    except Exception as e:
        logger.warning(f"DeepFace embedding failed: {e}")
    return None


def get_embedding_opencv(face_crop: np.ndarray) -> Optional[np.ndarray]:
    """
    Fallback: flatten + normalize a resized grayscale crop as a simple descriptor.
    Less accurate than FaceNet but works with no GPU.
    """
    try:
        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (64, 64))
        flat = resized.flatten().astype(np.float32)
        return l2_normalize(flat)
    except Exception as e:
        logger.warning(f"OpenCV embedding failed: {e}")
    return None


def get_embedding(face_crop: np.ndarray) -> Optional[np.ndarray]:
    if DEEPFACE_AVAILABLE:
        return get_embedding_deepface(face_crop)
    return get_embedding_opencv(face_crop)


# ── Enrollment ────────────────────────────────────────────────────────────────

def enroll_from_images(b64_images: list) -> tuple:
    """
    Extract embedding from multiple base64 images.
    Averages all successful embeddings for a more robust representation.
    Returns (averaged_embedding, num_successful).
    """
    embeddings = []
    for b64 in b64_images:
        try:
            frame = decode_base64_image(b64)
            faces = detect_faces_opencv(frame)
            if not faces:
                continue
            # Use the largest detected face
            face = max(faces, key=lambda f: f['w'] * f['h'])
            x, y, w, h = face['x'], face['y'], face['w'], face['h']
            # Add margin around face
            margin = int(0.1 * w)
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(frame.shape[1], x + w + margin)
            y2 = min(frame.shape[0], y + h + margin)
            crop = frame[y1:y2, x1:x2]
            emb = get_embedding(crop)
            if emb is not None:
                embeddings.append(emb)
        except Exception as e:
            logger.warning(f"Failed to process enrollment image: {e}")

    if not embeddings:
        return None, 0

    avg = np.mean(embeddings, axis=0).astype(np.float32)
    avg = l2_normalize(avg)
    return avg, len(embeddings)


# ── Recognition ───────────────────────────────────────────────────────────────

def recognize_frame(
    b64_frame: str,
    enrolled_students: list,
    threshold: float = 0.55
) -> list:
    """
    Detect all faces in frame, match each against enrolled students.
    Returns list of recognition results.
    """
    try:
        frame = decode_base64_image(b64_frame)
    except Exception as e:
        logger.error(f"Frame decode error: {e}")
        return []

    faces = detect_faces_opencv(frame)
    if not faces:
        return []

    # Pre-decode stored embeddings
    stored = []
    for s in enrolled_students:
        try:
            emb = decode_embedding(s['embedding_str'])
            stored.append({'db_id': s['db_id'], 'student_id': s['student_id'], 'name': s['name'], 'emb': emb})
        except Exception:
            pass

    results = []
    for face in faces:
        x, y, w, h = face['x'], face['y'], face['w'], face['h']
        margin = int(0.1 * w)
        x1, y1 = max(0, x - margin), max(0, y - margin)
        x2, y2 = min(frame.shape[1], x + w + margin), min(frame.shape[0], y + h + margin)
        crop = frame[y1:y2, x1:x2]

        query_emb = get_embedding(crop)
        match = None

        if query_emb is not None and stored:
            best_sim = -1.0
            best = None
            for s in stored:
                sim = cosine_similarity(query_emb, s['emb'])
                if sim > best_sim:
                    best_sim = sim
                    best = s

            if best and best_sim >= threshold:
                match = {
                    'db_id': best['db_id'],
                    'student_id': best['student_id'],
                    'name': best['name'],
                    'confidence': round(best_sim * 100, 1),
                }

        results.append({
            'face_region': {'x': x, 'y': y, 'w': w, 'h': h},
            'recognized': match is not None,
            'match': match,
        })

    return results
