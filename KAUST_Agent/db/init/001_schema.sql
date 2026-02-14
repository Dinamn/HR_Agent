-- Users / profile (one row per person)
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  full_name TEXT NOT NULL,
  full_name_ar TEXT,
  address TEXT,
  contact_phone TEXT,
  email TEXT,
  contract_type TEXT,          -- e.g., FullTime, PartTime
  start_date DATE,
  employment_title TEXT,
  base_salary NUMERIC(12,2),
  org_unit TEXT,
  direct_manager TEXT

);

-- Leave balances per user per year
CREATE TABLE leave_credits (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  year INT NOT NULL,
  annual_total INT NOT NULL,   -- total days granted
  annual_used INT NOT NULL DEFAULT 0
);

-- Leaves (requests)
CREATE TABLE leaves (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  days INT NOT NULL,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'PENDING', -- PENDING|APPROVED|REJECTED|CANCELLED
  created_at TIMESTAMP DEFAULT now()
);

-- Simple audit log
CREATE TABLE audit_log (
  id SERIAL PRIMARY KEY,
  user_id INT,
  action TEXT,
  details JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_leaves_user ON leaves(user_id);
