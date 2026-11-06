-- Healthcare Analytics and Patient Risk Indicator System (educational, synthetic data only)
-- Run as a MySQL admin:  mysql -u root -p < sql/schema.sql
-- Then create a LEAST-PRIVILEGE application user (see README step 3).

CREATE DATABASE IF NOT EXISTS health_analytics CHARACTER SET utf8mb4;
USE health_analytics;

CREATE TABLE IF NOT EXISTS departments (
    department_id   INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(64) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS patients (
    patient_id  INT AUTO_INCREMENT PRIMARY KEY,
    age_band    VARCHAR(16) NOT NULL,          -- e.g. '50-64' (never a date of birth)
    sex         VARCHAR(16) NULL,
    region_code VARCHAR(16) NULL,              -- coarse region, never an address
    CONSTRAINT chk_age_band CHECK (age_band IN ('0-17','18-34','35-49','50-64','65+'))
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS visits (
    visit_id      INT AUTO_INCREMENT PRIMARY KEY,
    patient_id    INT NOT NULL,
    department_id INT NOT NULL,
    visit_date    DATE NOT NULL,
    visit_type    VARCHAR(16) NOT NULL DEFAULT 'outpatient',
    CONSTRAINT fk_visit_patient FOREIGN KEY (patient_id)    REFERENCES patients(patient_id),
    CONSTRAINT fk_visit_dept    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    CONSTRAINT chk_visit_type   CHECK (visit_type IN ('outpatient','admission')),
    INDEX ix_visits_dept_date (department_id, visit_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS measurements (
    measurement_id   INT AUTO_INCREMENT PRIMARY KEY,
    patient_id       INT NOT NULL,
    measurement_date DATE NOT NULL,
    measure_type     VARCHAR(32) NOT NULL,
    value            DOUBLE NOT NULL,
    unit             VARCHAR(16) NOT NULL,
    CONSTRAINT fk_meas_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    CONSTRAINT uq_measurement UNIQUE (patient_id, measurement_date, measure_type),
    INDEX ix_meas_patient_type_date (patient_id, measure_type, measurement_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS risk_indicators (
    indicator_id    INT AUTO_INCREMENT PRIMARY KEY,
    patient_id      INT NOT NULL,
    rule_code       VARCHAR(48) NOT NULL,
    indicator_value DOUBLE NOT NULL,
    created_at      DATETIME NOT NULL,
    CONSTRAINT fk_ind_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    INDEX ix_ind_rule (rule_code)
) ENGINE=InnoDB;

-- Example analysis query (the Python code does the same with Pandas):
-- SELECT d.department_name, COUNT(*) AS visits, SUM(v.visit_type='admission') AS admissions
-- FROM visits v JOIN departments d USING (department_id)
-- GROUP BY d.department_name ORDER BY visits DESC;
