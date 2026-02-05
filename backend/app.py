from flask import Flask, request, jsonify, render_template
import json
from db import DB_PATH, get_conn, init_db

app = Flask(__name__)
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

@app.get("/admin")
def admin_dashboard():
    return render_template("admin.html")

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/enroll")
def enroll():
    data = request.get_json(force=True) or {}

    # Minimal required fields (adjust to your form)
    required = ["lrn", "fullName", "gradeLevel", "generalAve"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": f"Missing: {', '.join(missing)}"}), 400

    # --- Student core ---
    lrn = str(data["lrn"]).strip()
    fullName = str(data["fullName"]).strip()

    email = (data.get("email") or "").strip() or None
    contact = (data.get("contact") or "").strip() or None
    address = (data.get("address") or "").strip() or None

    # --- Extra student info (optional but in your form) ---
    dob = (data.get("dob") or "").strip() or None
    pob = (data.get("pob") or "").strip() or None
    sex = (data.get("sex") or "").strip() or None
    nationality = (data.get("nationality") or "").strip() or None

    # --- School history ---
    jhsGraduated = (data.get("jhsGraduated") or "").strip() or None
    dateGraduation = (data.get("dateGraduation") or "").strip() or None

    # --- Enrollment details ---
    gradeLevel = str(data["gradeLevel"]).strip()
    strand = (data.get("strand") or "").strip() or None

    tvlSpec = (data.get("tvlSpec") or "").strip() or None
    if strand == "TVL" and not tvlSpec:
        return jsonify({"ok": False, "error": "TVL specialization is required"}), 400

    generalAve = str(data["generalAve"]).strip()

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
    guardianTel = (data.get("guardianTel") or "").strip() or None
    guardianContact = (data.get("guardianContact") or "").strip() or None

    # --- Credentials + pledge ---
    credentialsSubmitted = (data.get("credentialsSubmitted") or "").strip() or None
    firstTimeAU = (data.get("firstTimeAU") or "").strip() or None
    enrolledYear = (data.get("enrolledYear") or "").strip() or None
    studentSignature = (data.get("studentSignature") or "").strip() or None

    with get_conn() as conn:
        cur = conn.cursor()
        try:
            # Upsert student by LRN
            cur.execute("""
                INSERT INTO students (
                    lrn, fullName, email, contact, address,
                    dob, pob, sex, nationality
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lrn) DO UPDATE SET
                    fullName=excluded.fullName,
                    email=excluded.email,
                    contact=excluded.contact,
                    address=excluded.address,
                    dob=excluded.dob,
                    pob=excluded.pob,
                    sex=excluded.sex,
                    nationality=excluded.nationality
            """, (
                lrn, fullName, email, contact, address,
                dob, pob, sex, nationality
            ))

            cur.execute("SELECT id FROM students WHERE lrn = ?", (lrn,))
            student_id = cur.fetchone()["id"]

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
def list_applications():
    status = request.args.get("status")  # optional filter

    q = """
      SELECT a.id, a.gradeLevel, a.strand, a.tvlSpec, a.generalAve, a.status, a.submitted_at,
             s.lrn, s.fullName
      FROM applications a
      JOIN students s ON s.id = a.student_id
    """
    params = ()
    if status:
        q += " WHERE a.status = ?"
        params = (status,)
    q += " ORDER BY a.id DESC LIMIT 200"

    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()

    items = []
    for r in rows:
        d = dict(r)
        items.append(d)

    return jsonify({"ok": True, "items": items})

@app.patch("/api/applications/<int:app_id>/status")
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
