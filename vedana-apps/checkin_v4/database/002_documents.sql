CREATE TABLE IF NOT EXISTS documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    gender VARCHAR(20) DEFAULT NULL,
    date_of_birth VARCHAR(20) DEFAULT NULL,
    identification_number VARCHAR(50) NOT NULL UNIQUE,
    address TEXT DEFAULT NULL,
    document_type VARCHAR(50) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO schema_migrations (version) VALUES ('002_documents');
