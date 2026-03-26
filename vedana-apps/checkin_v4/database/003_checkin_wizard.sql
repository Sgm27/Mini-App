-- 003_checkin_wizard.sql
-- Drop old documents table and create checkins + guests

DROP TABLE IF EXISTS documents;

CREATE TABLE checkins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_code VARCHAR(100) NOT NULL,
    room_type VARCHAR(100),
    num_guests INT NOT NULL,
    arrival_date VARCHAR(20) NOT NULL,
    departure_date VARCHAR(20) NOT NULL,
    contact_name VARCHAR(255),
    contact_phone VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'confirmed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE guests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    checkin_id INT NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    gender VARCHAR(20),
    date_of_birth VARCHAR(20),
    identification_number VARCHAR(50) NOT NULL,
    address TEXT,
    document_type VARCHAR(50),
    nationality VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_guests_checkin FOREIGN KEY (checkin_id) REFERENCES checkins(id) ON DELETE CASCADE,
    CONSTRAINT uq_guest_per_checkin UNIQUE (checkin_id, identification_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
