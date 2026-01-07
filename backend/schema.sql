CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lrn TEXT UNIQUE NOT NULL,
  first_name TEXT NOT NULL,
  last_name TEXT NOT NULL,
  middle_name TEXT,
  email TEXT,
  phone TEXT,
  address TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL,
  school_year TEXT NOT NULL,
  grade_level TEXT NOT NULL,
  strand TEXT,
  status TEXT NOT NULL DEFAULT 'submitted',
  submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (student_id) REFERENCES students(id)
);

CREATE INDEX IF NOT EXISTS idx_applications_student_id ON applications(student_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
