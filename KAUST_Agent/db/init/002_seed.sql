INSERT INTO users (username, full_name, full_name_ar, address, contact_phone, email, contract_type, start_date, employment_title, base_salary, org_unit, direct_manager)
VALUES

('Dina', 'Dina Alromih', 'دينا الرميح' , 'Riyadh', '0563925640', 'dalromih@tahakom.com', 'FullTime', '2024-11-03', 'AI Developer', 0000, 'AI & Innovation','Salem Alelyani' ),
('Elaph', 'Elaph Alotaibi', 'ايلاف العتيبي', 'Riyadh', '0500000001', 'elaph@hr.sa', 'FullTime', '2024-11-03', 'AI Developer',0000, 'AI & Innovation','Salem Alelyani'),
('Lujain', 'Lujain Almansour', 'لجين المنصور', 'Jeddah', '0500000002', 'lujain@hr.sa', 'FullTime', '2024-12-09', 'AI Developer', 0000, 'AI & Innovation','Salem Alelyani' );

INSERT INTO leave_credits (user_id, year, annual_total, annual_used)
VALUES
(1, EXTRACT(YEAR FROM now())::int, 21, 5),
(2, EXTRACT(YEAR FROM now())::int, 21, 10),
(3, EXTRACT(YEAR FROM now())::int, 21, 15);

INSERT INTO leaves (user_id, start_date, end_date, days, reason, status)
VALUES
(1, '2025-04-10', '2025-04-12', 3, 'SickLeave', 'APPROVED'),
(1, '2025-07-01', '2025-07-03', 3, 'AnnualLeave', 'CANCELLED'),
(2, '2025-02-01', '2025-02-05', 5, 'Travel', 'APPROVED'),
(3, '2025-02-01', '2025-02-05', 5, 'SickLeave', 'APPROVED');

