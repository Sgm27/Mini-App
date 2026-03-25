-- Migration 002: Housekeeping QR Report Tables
-- Run via MCP mysql tool

CREATE TABLE IF NOT EXISTS room_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    room_id VARCHAR(50) NOT NULL,
    note_text TEXT NULL,
    voice_url VARCHAR(500) NULL,
    image_urls JSON NOT NULL,
    status ENUM('submitted', 'reviewed') DEFAULT 'submitted',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_room_id (room_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO schema_migrations (version) VALUES ('002');
