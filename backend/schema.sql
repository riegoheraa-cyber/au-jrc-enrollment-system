CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lrn TEXT NOT NULL,
  fullName TEXT NOT NULL,
  email TEXT,
  contact TEXT,
  address TEXT,
  dob TEXT,
  pob TEXT,
  sex TEXT,
  nationality TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL,

  -- enrollment details
  gradeLevel TEXT NOT NULL,
  strand TEXT,
  tvlSpec TEXT,
  generalAve TEXT,

  -- school history
  jhsGraduated TEXT,
  dateGraduation TEXT,

  -- medical info (store checkbox list as JSON string)
  medicalConditions TEXT,
  medicalOther TEXT,
  howSupported TEXT,

  -- parent / guardian info
  guardianName TEXT,
  guardianCivilStatus TEXT,
  guardianEmployment TEXT,
  guardianOccupation TEXT,
  guardianRelationship TEXT,
  guardianTel TEXT,
  guardianContact TEXT,

  -- credentials + pledge
  credentialsSubmitted TEXT,
  firstTimeAU TEXT,
  enrolledYear TEXT,
  studentSignature TEXT,

  status TEXT NOT NULL DEFAULT 'submitted',
  submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,

  FOREIGN KEY (student_id) REFERENCES students(id)
);

CREATE INDEX IF NOT EXISTS idx_applications_student_id ON applications(student_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

CREATE INDEX IF NOT EXISTS idx_students_lrn ON students(lrn);
CREATE INDEX IF NOT EXISTS idx_students_fullName ON students(fullName);
