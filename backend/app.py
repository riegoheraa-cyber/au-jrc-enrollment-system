import os
import secrets
import time
from functools import wraps
from pathlib import Path
from uuid import uuid4
from flask import Flask, request, jsonify, render_template, redirect, session, url_for
import json
from werkzeug.utils import secure_filename
from db import DB_PATH, get_conn, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-admin-secret-change-me")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = int(os.environ.get("ADMIN_SESSION_TIMEOUT_SECONDS", "3600"))

_configured_admin_path = (os.environ.get("ADMIN_PATH") or "internal-portal").strip().strip("/")
ADMIN_PATH = f"/{_configured_admin_path or 'internal-portal'}"

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
ADMIN_LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("ADMIN_LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
ADMIN_LOGIN_RATE_LIMIT_MAX_ATTEMPTS = int(os.environ.get("ADMIN_LOGIN_RATE_LIMIT_MAX_ATTEMPTS", "5"))
_admin_login_attempts = {}

DEFAULT_SITE_CONTENT = {
    "hero_slides": [
        {
            "category": "Arellano University Jose Rizal Campus",
            "title": "Championing Academic Excellence Since 1938",
            "description": "Join a community rooted in tradition, service, and student-centered learning for every Arellanista.",
            "button_text": "",
            "button_link": "",
        },
        {
            "category": "University Updates",
            "title": "Admissions Open for Senior High School",
            "description": "We welcome incoming Grade 11 students and transferees with flexible learning options and student support.",
            "button_text": "View Admission Requirements",
            "button_link": "#requirements",
        },
        {
            "category": "Tatak Arellano",
            "title": "Affordable and Accessible Quality Education",
            "description": "Experience AU's commitment to holistic development through values formation, leadership, and innovation.",
            "button_text": "Learn More About AU",
            "button_link": "#about-us",
        },
    ],
    "highlights": [
        {
            "title": "Admissions & Enrollment",
            "description": "Complete your application, submit requirements, and track your enrollment journey in one place.",
            "link_text": "Requirements",
            "link": "#requirements",
        },
        {
            "title": "Academic Programs",
            "description": "Explore tracks and strands designed to prepare learners for college, careers, and lifelong success.",
            "link_text": "View Programs",
            "link": "#programs",
        },
        {
            "title": "Campus Community",
            "description": "Stay connected with AU culture, student life, and opportunities that nurture leadership and service.",
            "link_text": "Campus Updates",
            "link": "https://www.facebook.com/aujoserizal",
        },
    ],
    "enrollment_banner": {
        "title": "ENROLLMENT ONGOING FOR SENIOR HIGH",
        "subtitle": "2ND SEMESTER | S.Y. 2025-2026",
        "bullets": [
            "New students and transferees accepted.",
            "No Tuition Fee / No Top-Up (For eligible voucher holders)",
            "No Entrance Exam",
            "No Minimum Grade Requirement",
            "Flexible Learning Modality",
        ],
        "offer_title": "Easy Crediting of Subjects for",
        "offer_emphasis": "Transferees",
        "offer_subtitle": "No Tuition Fee Increase",
    },
    "requirements": {
        "title": "Admission Requirements",
        "intro": "Please prepare the following documents for Senior High School admission.",
        "items": [
            "PSA Birth Certificate",
            "ESC Certificate (For Completers from Private Schools)",
            "Certificate of Completion (For Completers from Public Schools)",
            "2x2 picture",
            "Form 138/Report Card",
        ],
    },
    "programs": [
        {"name": "STEM (Science, Technology, Engineering, and Mathematics)", "category": "Academic Track", "description": "The STEM strand is ideal for students who enjoy science and math. It builds a strong foundation for careers in engineering, medicine, and technology.", "image": "../static/assets/images/STEM.jpg"},
        {"name": "HUMSS (Humanities and Social Sciences)", "category": "Academic Track", "description": "The HUMSS strand is for students interested in people, culture, and society. It prepares learners for careers in law, education, communication, and public service.", "image": "../static/assets/images/HUMSS.jpg"},
        {"name": "GAS (General Academic Strand)", "category": "Academic Track", "description": "The GAS strand offers a balanced mix of subjects from different disciplines. It is best for students exploring their interests before choosing a specific college path.", "image": "../static/assets/images/GAS.jpg"},
        {"name": "ABM (Accountancy, Business, and Management)", "category": "Academic Track", "description": "The ABM strand focuses on business, finance, and entrepreneurship. It prepares students for college programs and careers in management, marketing, and accounting.", "image": "../static/assets/images/ABM.jpg"},
        {"name": "ICT (Information and Communications Technology)", "category": "Technical-Vocational-Livelihood (TVL)", "description": "The ICT strand develops skills in programming, web development, and networking. It prepares students for careers in IT, software development, and digital technology.", "image": "../static/assets/images/ICT.jpg"},
        {"name": "HE (Home Economics)", "category": "Technical-Vocational-Livelihood (TVL)", "description": "The HE strand builds practical skills in hospitality, cookery, and home management. It supports career paths in culinary arts, tourism, fashion, and small business.", "image": "../static/assets/images/HE.jpg"},
    ],
    "announcements": [
        {"title": "Enrollment for S.Y. 2025-2026", "description": "Application is now open for Senior High School with support for new students and transferees."},
        {"title": "No Entrance Examination", "description": "Qualified learners may proceed directly with admission requirements and online application."},
        {"title": "Flexible Learning Modality", "description": "AU supports learners through adaptable delivery and guidance to help students thrive."},
    ],
    "about": {
        "title": "About Arellano University",
        "paragraphs": [
            "Arellano University was founded in 1938, and its Jose Rizal Campus in Malabon was established to provide accessible and quality education to students in the northern part of Metro Manila.",
            "The campus is named after José Rizal, the national hero of the Philippines, in honor of his contributions to education and the nation.",
            "Since its establishment, the campus has been committed to promoting academic excellence and offering opportunities for personal and intellectual growth.",
        ],
    },
    "footer": {
        "logo": "https://www.arellano.edu.ph/images/Arellano_University_New_Logo.png",
        "address_lines": [
            "ARELLANO UNIVERSITY",
            "Gov. Pascual Avenue, Concepcion,",
            "Malabon City, Metro Manila",
            "8-579-3635 or 8-921-2744",
        ],
        "facebook": "https://www.facebook.com/aujoserizal",
        "instagram": "https://www.instagram.com/tatakarellano",
    },
}



UPLOAD_DIR = Path(__file__).resolve().parent / "static" / "uploads" / "site-content"
ALLOWED_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

DEFAULT_SITE_CONTENT = {
    "hero_slides": [
        {
            "category": "Arellano University Jose Rizal Campus",
            "title": "Championing Academic Excellence Since 1938",
            "description": "Join a community rooted in tradition, service, and student-centered learning for every Arellanista.",
            "button_text": "",
            "button_link": "",
            "image": "../static/assets/images/banner-item-01.jpg",
        },
        {
            "category": "University Updates",
            "title": "Admissions Open for Senior High School",
            "description": "We welcome incoming Grade 11 students and transferees with flexible learning options and student support.",
            "button_text": "View Admission Requirements",
            "button_link": "#requirements",
            "image": "../static/assets/images/banner-item-02.jpg",
        },
        {
            "category": "Tatak Arellano",
            "title": "Affordable and Accessible Quality Education",
            "description": "Experience AU's commitment to holistic development through values formation, leadership, and innovation.",
            "button_text": "Learn More About AU",
            "button_link": "#about-us",
            "image": "../static/assets/images/banner-item-03.jpg",
        },
    ],
    "highlights": [
        {
            "title": "Admissions & Enrollment",
            "description": "Complete your application, submit requirements, and track your enrollment journey in one place.",
            "link_text": "Requirements",
            "link": "#requirements",
        },
        {
            "title": "Academic Programs",
            "description": "Explore tracks and strands designed to prepare learners for college, careers, and lifelong success.",
            "link_text": "View Programs",
            "link": "#programs",
        },
        {
            "title": "Campus Community",
            "description": "Stay connected with AU culture, student life, and opportunities that nurture leadership and service.",
            "link_text": "Campus Updates",
            "link": "https://www.facebook.com/aujoserizal",
        },
    ],
    "enrollment_banner": {
        "title": "ENROLLMENT ONGOING FOR SENIOR HIGH",
        "subtitle": "2ND SEMESTER | S.Y. 2025-2026",
        "bullets": [
            "New students and transferees accepted.",
            "No Tuition Fee / No Top-Up (For eligible voucher holders)",
            "No Entrance Exam",
            "No Minimum Grade Requirement",
            "Flexible Learning Modality",
        ],
        "offer_title": "Easy Crediting of Subjects for",
        "offer_emphasis": "Transferees",
        "offer_subtitle": "No Tuition Fee Increase",
    },
    "requirements": {
        "title": "Admission Requirements",
        "intro": "Please prepare the following documents for Senior High School admission.",
        "items": [
            "PSA Birth Certificate",
            "ESC Certificate (For Completers from Private Schools)",
            "Certificate of Completion (For Completers from Public Schools)",
            "2x2 picture",
            "Form 138/Report Card",
        ],
    },
    "programs": [
        {"name": "STEM (Science, Technology, Engineering, and Mathematics)", "category": "Academic Track", "description": "The STEM strand is ideal for students who enjoy science and math. It builds a strong foundation for careers in engineering, medicine, and technology.", "image": "../static/assets/images/STEM.jpg"},
        {"name": "HUMSS (Humanities and Social Sciences)", "category": "Academic Track", "description": "The HUMSS strand is for students interested in people, culture, and society. It prepares learners for careers in law, education, communication, and public service.", "image": "../static/assets/images/HUMSS.jpg"},
        {"name": "GAS (General Academic Strand)", "category": "Academic Track", "description": "The GAS strand offers a balanced mix of subjects from different disciplines. It is best for students exploring their interests before choosing a specific college path.", "image": "../static/assets/images/GAS.jpg"},
        {"name": "ABM (Accountancy, Business, and Management)", "category": "Academic Track", "description": "The ABM strand focuses on business, finance, and entrepreneurship. It prepares students for college programs and careers in management, marketing, and accounting.", "image": "../static/assets/images/ABM.jpg"},
        {"name": "ICT (Information and Communications Technology)", "category": "Technical-Vocational-Livelihood (TVL)", "description": "The ICT strand develops skills in programming, web development, and networking. It prepares students for careers in IT, software development, and digital technology.", "image": "../static/assets/images/ICT.jpg"},
        {"name": "HE (Home Economics)", "category": "Technical-Vocational-Livelihood (TVL)", "description": "The HE strand builds practical skills in hospitality, cookery, and home management. It supports career paths in culinary arts, tourism, fashion, and small business.", "image": "../static/assets/images/HE.jpg"},
    ],
    "announcements": [
        {"title": "Enrollment for S.Y. 2025-2026", "description": "Application is now open for Senior High School with support for new students and transferees."},
        {"title": "No Entrance Examination", "description": "Qualified learners may proceed directly with admission requirements and online application."},
        {"title": "Flexible Learning Modality", "description": "AU supports learners through adaptable delivery and guidance to help students thrive."},
    ],
    "about": {
        "title": "About Arellano University",
        "paragraphs": [
            "Arellano University was founded in 1938, and its Jose Rizal Campus in Malabon was established to provide accessible and quality education to students in the northern part of Metro Manila.",
            "The campus is named after José Rizal, the national hero of the Philippines, in honor of his contributions to education and the nation.",
            "Since its establishment, the campus has been committed to promoting academic excellence and offering opportunities for personal and intellectual growth.",
        ],
    },
    "footer": {
        "logo": "https://www.arellano.edu.ph/images/Arellano_University_New_Logo.png",
        "address_lines": [
            "ARELLANO UNIVERSITY",
            "Gov. Pascual Avenue, Concepcion,",
            "Malabon City, Metro Manila",
            "8-579-3635 or 8-921-2744",
        ],
        "facebook": "https://www.facebook.com/aujoserizal",
        "instagram": "https://www.instagram.com/tatakarellano",
    },
}



UPLOAD_DIR = Path(__file__).resolve().parent / "static" / "uploads" / "site-content"
ALLOWED_UPLOAD_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

DEFAULT_SITE_CONTENT = {
    "hero_slides": [
        {
            "category": "Arellano University Jose Rizal Campus",
            "title": "Championing Academic Excellence Since 1938",
            "description": "Join a community rooted in tradition, service, and student-centered learning for every Arellanista.",
            "button_text": "",
            "button_link": "",
            "image": "../static/assets/images/banner-item-01.jpg",
        },
        {
            "category": "University Updates",
            "title": "Admissions Open for Senior High School",
            "description": "We welcome incoming Grade 11 students and transferees with flexible learning options and student support.",
            "button_text": "View Admission Requirements",
            "button_link": "#requirements",
            "image": "../static/assets/images/banner-item-02.jpg",
        },
        {
            "category": "Tatak Arellano",
            "title": "Affordable and Accessible Quality Education",
            "description": "Experience AU's commitment to holistic development through values formation, leadership, and innovation.",
            "button_text": "Learn More About AU",
            "button_link": "#about-us",
            "image": "../static/assets/images/banner-item-03.jpg",
        },
    ],
    "highlights": [
        {
            "title": "Admissions & Enrollment",
            "description": "Complete your application, submit requirements, and track your enrollment journey in one place.",
            "link_text": "Requirements",
            "link": "#requirements",
        },
        {
            "title": "Academic Programs",
            "description": "Explore tracks and strands designed to prepare learners for college, careers, and lifelong success.",
            "link_text": "View Programs",
            "link": "#programs",
        },
        {
            "title": "Campus Community",
            "description": "Stay connected with AU culture, student life, and opportunities that nurture leadership and service.",
            "link_text": "Campus Updates",
            "link": "https://www.facebook.com/aujoserizal",
        },
    ],
    "enrollment_banner": {
        "title": "ENROLLMENT ONGOING FOR SENIOR HIGH",
        "subtitle": "2ND SEMESTER | S.Y. 2025-2026",
        "bullets": [
            "New students and transferees accepted.",
            "No Tuition Fee / No Top-Up (For eligible voucher holders)",
            "No Entrance Exam",
            "No Minimum Grade Requirement",
            "Flexible Learning Modality",
        ],
        "offer_title": "Easy Crediting of Subjects for",
        "offer_emphasis": "Transferees",
        "offer_subtitle": "No Tuition Fee Increase",
    },
    "requirements": {
        "title": "Admission Requirements",
        "intro": "Please prepare the following documents for Senior High School admission.",
        "items": [
            "PSA Birth Certificate",
            "ESC Certificate (For Completers from Private Schools)",
            "Certificate of Completion (For Completers from Public Schools)",
            "2x2 picture",
            "Form 138/Report Card",
        ],
    },
    "programs": [
        {"name": "STEM (Science, Technology, Engineering, and Mathematics)", "category": "Academic Track", "description": "The STEM strand is ideal for students who enjoy science and math. It builds a strong foundation for careers in engineering, medicine, and technology.", "image": "../static/assets/images/STEM.jpg"},
        {"name": "HUMSS (Humanities and Social Sciences)", "category": "Academic Track", "description": "The HUMSS strand is for students interested in people, culture, and society. It prepares learners for careers in law, education, communication, and public service.", "image": "../static/assets/images/HUMSS.jpg"},
        {"name": "GAS (General Academic Strand)", "category": "Academic Track", "description": "The GAS strand offers a balanced mix of subjects from different disciplines. It is best for students exploring their interests before choosing a specific college path.", "image": "../static/assets/images/GAS.jpg"},
        {"name": "ABM (Accountancy, Business, and Management)", "category": "Academic Track", "description": "The ABM strand focuses on business, finance, and entrepreneurship. It prepares students for college programs and careers in management, marketing, and accounting.", "image": "../static/assets/images/ABM.jpg"},
        {"name": "ICT (Information and Communications Technology)", "category": "Technical-Vocational-Livelihood (TVL)", "description": "The ICT strand develops skills in programming, web development, and networking. It prepares students for careers in IT, software development, and digital technology.", "image": "../static/assets/images/ICT.jpg"},
        {"name": "HE (Home Economics)", "category": "Technical-Vocational-Livelihood (TVL)", "description": "The HE strand builds practical skills in hospitality, cookery, and home management. It supports career paths in culinary arts, tourism, fashion, and small business.", "image": "../static/assets/images/HE.jpg"},
    ],
    "announcements": [
        {"title": "Enrollment for S.Y. 2025-2026", "description": "Application is now open for Senior High School with support for new students and transferees."},
        {"title": "No Entrance Examination", "description": "Qualified learners may proceed directly with admission requirements and online application."},
        {"title": "Flexible Learning Modality", "description": "AU supports learners through adaptable delivery and guidance to help students thrive."},
    ],
    "about": {
        "title": "About Arellano University",
        "paragraphs": [
            "Arellano University was founded in 1938, and its Jose Rizal Campus in Malabon was established to provide accessible and quality education to students in the northern part of Metro Manila.",
            "The campus is named after José Rizal, the national hero of the Philippines, in honor of his contributions to education and the nation.",
            "Since its establishment, the campus has been committed to promoting academic excellence and offering opportunities for personal and intellectual growth.",
        ],
    },
    "footer": {
        "logo": "https://www.arellano.edu.ph/images/Arellano_University_New_Logo.png",
        "address_lines": [
            "ARELLANO UNIVERSITY",
            "Gov. Pascual Avenue, Concepcion,",
            "Malabon City, Metro Manila",
            "8-579-3635 or 8-921-2744",
        ],
        "facebook": "https://www.facebook.com/aujoserizal",
        "instagram": "https://www.instagram.com/tatakarellano",
    },
}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Authentication required"}), 401
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


def _client_identifier() -> str:
    forwarded_for = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded_for or request.remote_addr or "unknown"


def _is_rate_limited(login_identifier: str) -> bool:
    now = time.time()
    attempts = _admin_login_attempts.get(login_identifier, [])
    attempts = [attempt_ts for attempt_ts in attempts if now - attempt_ts < ADMIN_LOGIN_RATE_LIMIT_WINDOW_SECONDS]
    _admin_login_attempts[login_identifier] = attempts
    return len(attempts) >= ADMIN_LOGIN_RATE_LIMIT_MAX_ATTEMPTS


def _record_failed_login(login_identifier: str) -> None:
    now = time.time()
    attempts = _admin_login_attempts.setdefault(login_identifier, [])
    attempts.append(now)


def _new_csrf_token() -> str:
    token = secrets.token_urlsafe(32)
    session["admin_login_csrf"] = token
    return token


def _validate_csrf_token(submitted_token: str) -> bool:
    expected_token = session.get("admin_login_csrf")
    if not expected_token or not submitted_token:
        return False
    return secrets.compare_digest(expected_token, submitted_token)


init_db()




def _merge_default_content(default_value, current_value):
    if isinstance(default_value, dict) and isinstance(current_value, dict):
        merged = dict(default_value)
        for key, value in current_value.items():
            if key in default_value:
                merged[key] = _merge_default_content(default_value[key], value)
            else:
                merged[key] = value
        return merged

    if isinstance(default_value, list) and isinstance(current_value, list):
        merged = []
        for idx, value in enumerate(current_value):
            if idx < len(default_value):
                merged.append(_merge_default_content(default_value[idx], value))
            else:
                merged.append(value)
        return merged

    return current_value

def _ensure_site_content_defaults():
    with get_conn() as conn:
        for key, value in DEFAULT_SITE_CONTENT.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO site_content (content_key, content_value)
                VALUES (?, ?)
                """,
                (key, json.dumps(value)),
            )
        conn.commit()


def _get_site_content() -> dict:
    data = dict(DEFAULT_SITE_CONTENT)
    with get_conn() as conn:
        rows = conn.execute("SELECT content_key, content_value FROM site_content").fetchall()
    for row in rows:
        try:
            parsed_value = json.loads(row["content_value"])
            data[row["content_key"]] = _merge_default_content(DEFAULT_SITE_CONTENT.get(row["content_key"]), parsed_value)
        except json.JSONDecodeError:
            data[row["content_key"]] = DEFAULT_SITE_CONTENT.get(row["content_key"])
    return data


_ensure_site_content_defaults()
print(">>> USING DB:", DB_PATH)

@app.get("/")
def home():
    return render_template("index.html", content=_get_site_content())

@app.get("/enroll")
def enroll_now():
    return render_template("enroll.html")

@app.get("/requirements")
def requirements():
    return redirect(url_for("home") + "#requirements")

@app.get(f"{ADMIN_PATH}/login")
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_applications"))
    csrf_token = _new_csrf_token()
    return render_template("admin_login.html", error=None, csrf_token=csrf_token)


@app.post(f"{ADMIN_PATH}/login")
def admin_login_submit():
    login_identifier = f"{_client_identifier()}:{(request.form.get('username') or '').strip().lower()}"
    if _is_rate_limited(login_identifier):
        csrf_token = _new_csrf_token()
        return render_template("admin_login.html", error="Invalid credentials or request.", csrf_token=csrf_token), 429

    submitted_csrf = request.form.get("csrf_token") or ""
    if not _validate_csrf_token(submitted_csrf):
        _record_failed_login(login_identifier)
        csrf_token = _new_csrf_token()
        return render_template("admin_login.html", error="Invalid credentials or request.", csrf_token=csrf_token), 400

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session.clear()
        session["admin_logged_in"] = True
        session.permanent = True
        next_url = (request.form.get("next") or request.args.get("next") or url_for("admin_applications")).strip()
        if not next_url.startswith(ADMIN_PATH):
            next_url = url_for("admin_applications")
        return redirect(next_url)

    _record_failed_login(login_identifier)
    csrf_token = _new_csrf_token()
    return render_template("admin_login.html", error="Invalid credentials or request.", csrf_token=csrf_token), 401


@app.post(f"{ADMIN_PATH}/logout")
@login_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.get(f"{ADMIN_PATH}")
@login_required
def admin_dashboard():
    return redirect(url_for("admin_applications"))


@app.get(f"{ADMIN_PATH}/applications")
@login_required
def admin_applications():
    return render_template("admin.html", page="applications")


@app.get(f"{ADMIN_PATH}/content-manager")
@login_required
def admin_content_manager():
    return render_template("admin.html", page="content")


@app.get("/admin")
def legacy_admin_route_not_found():
    return jsonify({"ok": False, "error": "Not found"}), 404


@app.get("/admin/login")
@app.get("/admin-login")
def legacy_admin_login_route_not_found():
    return jsonify({"ok": False, "error": "Not found"}), 404


@app.get("/api/site-content")
@login_required
def get_site_content():
    return jsonify({"ok": True, "item": _get_site_content()})


@app.put("/api/site-content/<string:content_key>")
@login_required
def update_site_content(content_key: str):
    if content_key not in DEFAULT_SITE_CONTENT:
        return jsonify({"ok": False, "error": "Unknown content section."}), 404

    payload = request.get_json(force=True) or {}
    if "value" not in payload:
        return jsonify({"ok": False, "error": "Missing `value` in request body."}), 400

    try:
        serialized = json.dumps(payload["value"])
    except TypeError:
        return jsonify({"ok": False, "error": "Content must be JSON-serializable."}), 400

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO site_content (content_key, content_value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(content_key) DO UPDATE SET
                content_value = excluded.content_value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (content_key, serialized),
        )
        conn.commit()

    return jsonify({"ok": True})



@app.post("/api/site-content/upload")
@login_required
def upload_site_content_asset():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"ok": False, "error": "No file uploaded."}), 400

    original_name = secure_filename(upload.filename)
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        return jsonify({"ok": False, "error": "Unsupported file type. Use png, jpg, jpeg, webp, or gif."}), 400

    asset_scope = (request.form.get("scope") or "asset").strip().lower()
    prefix = "slide" if asset_scope == "slide" else "program" if asset_scope == "program" else "asset"

    file_name = f"{prefix}-{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / file_name
    upload.save(file_path)

    file_url = f"../static/uploads/site-content/{file_name}"
    return jsonify({"ok": True, "url": file_url})
@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/enroll")
def enroll():
    data = request.get_json(force=True) or {}

    def clean(v):
        if v is None:
            return ""
        s = str(v).strip()
        if s.lower() in {"", "none", "null", "undefined"}:
            return ""
        return s

    def pick(*keys):
        for key in keys:
            v = clean(data.get(key))
            if v:
                return v
        return ""

    # Normalize payload aliases coming from different frontend versions
    lrn = pick("lrn")
    fullName = pick("fullName")
    if not fullName:
        fullName = " ".join(filter(None, [pick("surname"), pick("givenName"), pick("middleName")]))

    gradeLevel = pick("gradeLevel", "yearLevel") or "N/A"
    generalAve = pick("generalAve", "generalAverage")

    track = pick("track")
    strand = pick("strand")
    if not strand and track == "Academic Track":
        strand = pick("academicStrand")
    elif not strand and track == "TVL Track":
        strand = "TVL"

    # Minimal required fields
    required = {
        "lrn": lrn,
        "fullName": fullName,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        return jsonify({"ok": False, "error": f"Missing: {', '.join(missing)}"}), 400

    # --- Student core ---

    email = pick("email", "gmail") or None
    contact = pick("contact", "contactNo") or None
    address = (data.get("address") or "").strip() or None

    if contact and (not contact.isdigit() or len(contact) != 11):
        return jsonify({"ok": False, "error": "Contact number must be exactly 11 digits."}), 400

    # --- Extra student info (optional but in your form) ---
    dob = (data.get("dob") or "").strip() or None
    pob = (data.get("pob") or "").strip() or None
    sex = (data.get("sex") or "").strip() or None
    nationality = (data.get("nationality") or "").strip() or None

    # --- School history ---
    jhsGraduated = (data.get("jhsGraduated") or "").strip() or None
    dateGraduation = (data.get("dateGraduation") or "").strip() or None

    # --- Enrollment details ---
    strand = strand or None

    tvlSpec = (data.get("tvlSpec") or "").strip() or None
    if strand == "TVL" and not tvlSpec:
        return jsonify({"ok": False, "error": "TVL specialization is required"}), 400

    generalAve = generalAve

    # --- Medical ---
    medicalConditions = data.get("medicalConditions") or []
    if not isinstance(medicalConditions, list):
        # if client accidentally sends a string
        medicalConditions = [str(medicalConditions)]
    medicalOther = (data.get("medicalOther") or "").strip() or None
    howSupported = (data.get("howSupported") or "").strip() or None

    # --- Guardian ---
    guardianName = (data.get("guardianName") or "").strip() or None
    guardianCivilStatus = pick("guardianCivilStatus", "civilStatus") or None
    guardianEmployment = pick("guardianEmployment") or None
    guardianOccupation = pick("guardianOccupation", "occupation") or None
    guardianRelationship = pick("guardianRelationship", "relationship") or None
    guardianTel = pick("guardianTel", "telNo") or None
    guardianContact = pick("guardianContact", "cellphoneNo") or None

    if guardianTel and (not guardianTel.isdigit()):
        return jsonify({"ok": False, "error": "Telephone number must contain digits only."}), 400

    if guardianContact and (not guardianContact.isdigit() or len(guardianContact) != 11):
        return jsonify({"ok": False, "error": "Guardian cellphone number must be exactly 11 digits."}), 400

    # --- Credentials + pledge ---
    raw_credentials = data.get("credentialsSubmitted") or []
    if isinstance(raw_credentials, list):
        picked_credentials = [str(v).strip() for v in raw_credentials if str(v).strip()]
    else:
        picked_credentials = [str(raw_credentials).strip()] if str(raw_credentials).strip() else []
    credentialsSubmitted = ", ".join(picked_credentials) if picked_credentials else None
    firstTimeAU = (data.get("firstTimeAU") or "").strip() or None
    enrolledYear = (data.get("enrolledYear") or "").strip() or None
    studentSignature = (data.get("studentSignature") or "").strip() or None

    with get_conn() as conn:
        cur = conn.cursor()
        try:
            # Insert student by LRN (do not update existing records)
            cur.execute("""
                INSERT INTO students (
                    lrn, fullName, email, contact, address,
                    dob, pob, sex, nationality
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lrn, fullName, email, contact, address,
                dob, pob, sex, nationality
            ))

            student_id = cur.lastrowid

            # Insert application (store the rest here)
            cur.execute("""
                INSERT INTO applications (
                    student_id, gradeLevel, strand, tvlSpec, generalAve, status,

                    jhsGraduated, dateGraduation,

                    medicalConditions, medicalOther, howSupported,

                    guardianName, guardianCivilStatus, guardianEmployment,
                    guardianOccupation, guardianRelationship, guardianTel, guardianContact,

                    credentialsSubmitted, firstTimeAU, enrolledYear, studentSignature
                )
                VALUES (
                    ?, ?, ?, ?, ?, 'submitted',
                    ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
            """, (
                student_id, gradeLevel, strand, tvlSpec, generalAve,

                jhsGraduated, dateGraduation,

                json.dumps(medicalConditions), medicalOther, howSupported,

                guardianName, guardianCivilStatus, guardianEmployment,
                guardianOccupation, guardianRelationship, guardianTel, guardianContact,

                credentialsSubmitted, firstTimeAU, enrolledYear, studentSignature
            ))

            application_id = cur.lastrowid
            conn.commit()

        except Exception as e:
            conn.rollback()
            return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify({"ok": True, "application_id": application_id})

@app.get("/api/applications")
@login_required
def list_applications():
    status = (request.args.get("status") or "").strip()  # optional filter
    strand = (request.args.get("strand") or "").strip()  # optional filter

    q = """
      SELECT a.id, a.gradeLevel, a.strand, a.tvlSpec, a.generalAve, a.status, a.submitted_at,
             a.credentialsSubmitted, s.lrn, s.fullName
      FROM applications a
      JOIN students s ON s.id = a.student_id
    """
    params = []
    filters = []
    if status:
        filters.append("a.status = ?")
        params.append(status)
    if strand:
        filters.append("a.strand = ?")
        params.append(strand)

    if filters:
        q += " WHERE " + " AND ".join(filters)
    q += " ORDER BY a.id DESC LIMIT 200"

    with get_conn() as conn:
        rows = conn.execute(q, tuple(params)).fetchall()

    items = []
    for r in rows:
        d = dict(r)
        items.append(d)

    return jsonify({"ok": True, "items": items})


@app.get("/api/applications/<int:app_id>")
@login_required
def get_application_details(app_id: int):
    query = """
      SELECT
        a.id, a.student_id, a.gradeLevel, a.strand, a.tvlSpec, a.generalAve, a.status, a.submitted_at,
        a.jhsGraduated, a.dateGraduation,
        a.medicalConditions, a.medicalOther, a.howSupported,
        a.guardianName, a.guardianCivilStatus, a.guardianEmployment,
        a.guardianOccupation, a.guardianRelationship, a.guardianTel, a.guardianContact,
        a.credentialsSubmitted, a.firstTimeAU, a.enrolledYear, a.studentSignature,
        s.lrn, s.fullName, s.email, s.contact, s.address, s.dob, s.pob, s.sex, s.nationality
      FROM applications a
      JOIN students s ON s.id = a.student_id
      WHERE a.id = ?
      LIMIT 1
    """

    with get_conn() as conn:
        row = conn.execute(query, (app_id,)).fetchone()

    if not row:
        return jsonify({"ok": False, "error": "Application not found."}), 404

    details = dict(row)
    try:
        details["medicalConditions"] = json.loads(details.get("medicalConditions") or "[]")
    except json.JSONDecodeError:
        details["medicalConditions"] = []

    return jsonify({"ok": True, "item": details})

@app.patch("/api/applications/<int:app_id>/status")
@login_required
def update_status(app_id: int):
    data = request.get_json(force=True) or {}
    new_status = (data.get("status") or "").strip()

    allowed = {"submitted", "under_review", "approved", "rejected"}
    if new_status not in allowed:
        return jsonify({"ok": False, "error": f"Invalid status. Allowed: {sorted(list(allowed))}"}), 400

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE applications SET status = ? WHERE id = ?", (new_status, app_id))
        conn.commit()

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
