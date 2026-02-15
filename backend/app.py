import os
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, session, url_for
import json
from db import DB_PATH, get_conn, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-admin-secret-change-me")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "Authentication required"}), 401
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped_view


init_db()
print(">>> USING DB:", DB_PATH)

@app.get("/")
def home():
    return render_template("index.html")

@app.get("/enroll")
def enroll_now():
    return render_template("enroll.html")

@app.get("/requirements")
def requirements():
    return render_template("requirements.html")

@app.get("/admin/login")
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html", error=None)


@app.post("/admin/login")
def admin_login_submit():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        next_url = (request.form.get("next") or request.args.get("next") or url_for("admin_dashboard")).strip()
        if not next_url.startswith("/"):
            next_url = url_for("admin_dashboard")
        return redirect(next_url)

    return render_template("admin_login.html", error="Invalid admin username or password."), 401


@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.get("/admin")
@login_required
def admin_dashboard():
    return render_template("admin.html")

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

    email = (data.get("email") or "").strip() or None
    contact = (data.get("contact") or data.get("contactNo") or "").strip() or None
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
    guardianCivilStatus = (data.get("guardianCivilStatus") or "").strip() or None
    guardianEmployment = (data.get("guardianEmployment") or "").strip() or None
    guardianOccupation = (data.get("guardianOccupation") or "").strip() or None
    guardianRelationship = (data.get("guardianRelationship") or "").strip() or None
    guardianTel = (data.get("guardianTel") or data.get("telNo") or "").strip() or None
    guardianContact = (data.get("guardianContact") or data.get("cellphoneNo") or "").strip() or None

    if guardianTel and (not guardianTel.isdigit()):
        return jsonify({"ok": False, "error": "Telephone number must contain digits only."}), 400

    if guardianContact and (not guardianContact.isdigit() or len(guardianContact) != 11):
        return jsonify({"ok": False, "error": "Guardian cellphone number must be exactly 11 digits."}), 400

    # --- Credentials + pledge ---
    credentialsSubmitted = (data.get("credentialsSubmitted") or "").strip() or None
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
             s.lrn, s.fullName
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
