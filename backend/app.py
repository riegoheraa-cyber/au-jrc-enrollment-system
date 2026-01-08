from flask import Flask, request, jsonify, render_template
from db import DB_PATH, get_conn, init_db

app = Flask(__name__)
init_db()
print(">>> USING DB:", DB_PATH)
@app.get("/")
def home():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/enroll")
def enroll():
    data = request.get_json(force=True)

    # Minimal required fields (adjust to your form)
    required = ["lrn", "fullName", "gradeLevel"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": f"Missing: {', '.join(missing)}"}), 400

    lrn = data["lrn"].strip()
    fullName = data["fullName"].strip()

    email = (data.get("email") or "").strip() or None
    phone = (data.get("phone") or "").strip() or None
    address = (data.get("address") or "").strip() or None


    gradeLevel = data["gradeLevel"].strip()
    strand = (data.get("strand") or "").strip() or None

    with get_conn() as conn:
        cur = conn.cursor()
        try:
            # Upsert student by LRN
            cur.execute("""
                INSERT INTO students (lrn, fullName, email, phone, address)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(lrn) DO UPDATE SET
                    fullName=excluded.fullName,
                    
                    email=excluded.email,
                    phone=excluded.phone,
                    address=excluded.address
            """, (lrn, fullName, email, phone, address))

            cur.execute("SELECT id FROM students WHERE lrn = ?", (lrn,))
            student_id = cur.fetchone()["id"]

            cur.execute("""
                INSERT INTO applications (student_id, gradeLevel, strand, status)
                VALUES (?, ?, ?,  'submitted')
            """, (student_id, gradeLevel, strand))

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
      SELECT a.id, a.gradeLevel, a.strand, a.status, a.submitted_at,
             s.lrn, s.full name
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

    return jsonify({
        "ok": True,
        "items": [dict(r) for r in rows]
    })

@app.patch("/api/applications/<int:app_id>/status")
def update_status(app_id: int):
    data = request.get_json(force=True)
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
    app.run(debug=True) 