INSERT INTO users (username, full_name, full_name_ar, address, contact_phone, email, contract_type, start_date, employment_title, base_salary, org_unit)
VALUES

('Dina', 'Dina Alromih', 'دينا الرميح' ', 'Riyadh', '0563925640', 'dina@hr.sa', 'FullTime', '2024-11-03', 'AI Developer', 12000, 'AI & Innovation'),
('Elaph', 'Elaph Alotaibi', 'ايلاف العتيبي', 'Riyadh', '0500000001', 'elaph@hr.sa', 'FullTime', '2024-11-03', 'AI Developer', 12000, 'AI & Innovation'),
('Lujain', 'Lujain Almansour', 'لجين المنصور', 'Jeddah', '0500000002', 'lujain@hr.sa', 'FullTime', '2024-12-09', 'AI Developer', 12000, 'AI & Innovation');

INSERT INTO leave_credits (user_id, year, annual_total, annual_used)
VALUES
(1, EXTRACT(YEAR FROM now())::int, 21, 5),
(2, EXTRACT(YEAR FROM now())::int, 12, 2),
(3, EXTRACT(YEAR FROM now())::int, 30, 10);

INSERT INTO leaves (user_id, start_date, end_date, days, reason, status)
VALUES
(1, '2025-04-10', '2025-04-12', 3, 'Eid', 'APPROVED'),
(1, '2025-07-01', '2025-07-03', 3, 'Travel', 'CANCELLED'),
(2, '2025-02-01', '2025-02-05', 5, 'Family', 'APPROVED'),
(3, '2025-02-01', '2025-02-05', 5, 'SickLeave', 'APPROVED');

