CREATE DATABASE IF NOT EXISTS blood_bank;
USE blood_bank;

CREATE TABLE IF NOT EXISTS donors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    aadhar CHAR(12) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    blood_group ENUM('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') NOT NULL,
    age TINYINT UNSIGNED NOT NULL,
    height DECIMAL(5,2) NOT NULL,
    weight DECIMAL(5,2) NOT NULL,
    address TEXT NOT NULL,
    phone_number CHAR(10) NOT NULL,
    bad_habits ENUM('Yes', 'No') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_age CHECK (age BETWEEN 18 AND 55),
    CONSTRAINT chk_height CHECK (height BETWEEN 120 AND 220),
    CONSTRAINT chk_weight CHECK (weight BETWEEN 45 AND 200)
);
