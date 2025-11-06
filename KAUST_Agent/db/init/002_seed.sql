INSERT INTO users (username, full_name, full_name_ar, address, contact_phone, email, contract_type, start_date, employment_title, base_salary, org_unit)
VALUES
('Elaph', 'Elaph Alotaibi', 'ايلاف العتيبي', 'Riyadh', '0500000001', 'elaph@acme.sa', 'FullTime', '2022-03-01', 'HR Specialist', 12000, 'HR'),
('khalid', 'Khalid Alharbi', 'خالد الحربي', 'Jeddah', '0500000002', 'khalid@acme.sa', 'FullTime', '2021-06-15', 'Engineer', 15000, 'Engineering');

INSERT INTO leave_credits (user_id, year, annual_total, annual_used)
VALUES
(1, EXTRACT(YEAR FROM now())::int, 21, 5),
(2, EXTRACT(YEAR FROM now())::int, 30, 10);

INSERT INTO leaves (user_id, start_date, end_date, days, reason, status)
VALUES
(1, '2025-04-10', '2025-04-12', 3, 'Eid', 'APPROVED'),
(1, '2025-07-01', '2025-07-03', 3, 'Travel', 'CANCELLED'),
(2, '2025-02-01', '2025-02-05', 5, 'Family', 'APPROVED');
