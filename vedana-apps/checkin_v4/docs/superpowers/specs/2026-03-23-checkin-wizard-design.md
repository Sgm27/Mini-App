# Check-in Wizard — Design Spec

## Overview

Extend the Smart OCR (checkin_v4) hotel check-in app by replacing the "Scan" tab with a 3-step check-in wizard. The wizard guides guests through: uploading a booking confirmation image, uploading identity documents, and reviewing/confirming all information before submission.

## Goals

- Streamline the check-in flow into a guided wizard experience
- Support OCR extraction from any booking confirmation format
- Support batch upload of identity documents with automatic profile merging by identification number
- Redesign the database to model bookings and guests properly
- Update the History tab to display check-in records grouped by booking

## Non-Goals

- Room management / auto-assignment (future phase)
- Excel/XML export for reception (future phase)
- Zalo notification integration (future phase)
- Chatbot conversational interface (future phase)

---

## Database Schema

Replace the existing `documents` table with two new tables:

### Table: `checkins`

| Column         | Type         | Constraints              |
|----------------|--------------|--------------------------|
| id             | INT          | PK, AUTO_INCREMENT       |
| booking_code   | VARCHAR(100) | NOT NULL                 |
| room_type      | VARCHAR(100) | nullable                 |
| num_guests     | INT          | NOT NULL                 |
| arrival_date   | VARCHAR(20)  | NOT NULL                 |
| departure_date | VARCHAR(20)  | NOT NULL                 |
| contact_name   | VARCHAR(255) | nullable                 |
| contact_phone  | VARCHAR(20)  | nullable                 |
| status         | VARCHAR(20)  | NOT NULL, DEFAULT 'confirmed' |
| created_at     | DATETIME     | DEFAULT CURRENT_TIMESTAMP |

### Table: `guests`

| Column                 | Type         | Constraints                    |
|------------------------|--------------|--------------------------------|
| id                     | INT          | PK, AUTO_INCREMENT             |
| checkin_id             | INT          | FK → checkins.id, NOT NULL     |
| full_name              | VARCHAR(255) | NOT NULL                       |
| gender                 | VARCHAR(20)  | nullable                       |
| date_of_birth          | VARCHAR(20)  | nullable                       |
| identification_number  | VARCHAR(50)  | NOT NULL                       |
| address                | TEXT         | nullable                       |
| document_type          | VARCHAR(50)  | nullable                       |
| nationality            | VARCHAR(100) | nullable                       |
| created_at             | DATETIME     | DEFAULT CURRENT_TIMESTAMP      |

**Composite unique constraint:** `UNIQUE(checkin_id, identification_number)` — prevents duplicate guests within the same check-in, but allows the same person across different check-ins (returning guests).

**Note on `nationality`:** The existing OCR pipeline does not extract nationality. This field will default to `null` and require manual input on the review form (Step 3). For passports, a future enhancement could add nationality extraction to the OCR prompts.

### Foreign Key Constraints

- `guests.checkin_id` → `checkins.id` with `ON DELETE CASCADE`

### Migration

- Drop table `documents` (destructive — acceptable for development; no production data exists yet)
- Create tables `checkins` and `guests`
- SQL migration file: `database/003_checkin_wizard.sql`

---

## Backend API

### New Endpoints

#### 1. `POST /api/ocr/booking`

Extract booking information from a confirmation image.

**Request:** `multipart/form-data` with `file` field (JPG, PNG, WEBP, max 10MB)

**Response 200:**
```json
{
  "booking_code": "WYN-2026-001",
  "room_type": "Deluxe King",
  "num_guests": 3,
  "arrival_date": "25/03/2026",
  "departure_date": "28/03/2026"
}
```

**Implementation:** New function in `ocr_service.py` using the configured OpenAI model (`settings.openai_model`) vision API with a prompt that extracts booking fields from any image format. Returns extracted fields; missing fields return `null`.

**Error responses:**
- `400` — Invalid file type or size
- `422` — Image does not appear to be a booking confirmation
- `500` — OCR processing error

#### 2. `POST /api/ocr/batch-extract`

Extract identity information from multiple document images, merging profiles by identification number.

**Request:** `multipart/form-data` with `files` field (multiple images)

**Response 200:**
```json
{
  "guests": [
    {
      "full_name": "Nguyen Van A",
      "gender": "Nam",
      "date_of_birth": "15/06/1990",
      "identification_number": "001090012345",
      "address": "Ha Noi",
      "document_type": "cccd",
      "nationality": "Viet Nam"
    }
  ],
  "total_profiles": 2
}
```

**Merge logic:** After extracting all images, group results by `identification_number`. For each group, merge fields: later images fill in fields that were `null` from earlier ones. This handles front + back of same document. When adding more images later (via "Them anh"), new extractions merge into the existing guest list using the same logic — matching by `identification_number`, filling null fields only (not overwriting existing values).

**Null identification_number handling:** If OCR fails to extract an identification number (returns null or "Khong xac dinh"), assign a temporary client-side UUID as a placeholder key. These profiles remain separate and are flagged to the user for manual correction on the review form.

**Implementation:** Calls existing `process_document()` for each file, then applies merge logic.

**Error responses:**
- `400` — No valid image files provided
- `422` — None of the images contain recognizable identity documents
- `500` — OCR processing error

#### 3. `POST /api/checkins`

Submit a complete check-in record.

**Request:**
```json
{
  "booking": {
    "booking_code": "WYN-2026-001",
    "room_type": "Deluxe King",
    "num_guests": 3,
    "arrival_date": "25/03/2026",
    "departure_date": "28/03/2026"
  },
  "contact": {
    "name": "Nguyen Van A",
    "phone": "0901234567"
  },
  "guests": [
    {
      "full_name": "Nguyen Van A",
      "gender": "Nam",
      "date_of_birth": "15/06/1990",
      "identification_number": "001090012345",
      "address": "Ha Noi",
      "document_type": "cccd",
      "nationality": "Viet Nam"
    }
  ]
}
```

**Response 201:**
```json
{
  "id": 1,
  "booking_code": "WYN-2026-001",
  "room_type": "Deluxe King",
  "num_guests": 3,
  "arrival_date": "25/03/2026",
  "departure_date": "28/03/2026",
  "contact_name": "Nguyen Van A",
  "contact_phone": "0901234567",
  "status": "confirmed",
  "created_at": "2026-03-23T10:00:00"
}
```

**Validation:**
- `arrival_date` and `departure_date` must be valid dates in DD/MM/YYYY format
- `departure_date` must be on or after `arrival_date`
- `num_guests` vs actual guest count: advisory only (frontend warning), not enforced by backend — allows flexibility for last-minute changes

**Error responses:**
- `400` — Validation failure (invalid dates, missing required fields)
- `500` — Database error

**Implementation:** Creates `checkins` record + associated `guests` records in a single transaction.

#### 4. `GET /api/checkins`

List all check-ins, newest first.

**Response 200:** Array of checkin summaries (id, booking_code, room_type, num_guests, arrival_date, departure_date, contact_name, contact_phone, status, created_at). Supports optional `limit` and `offset` query parameters for pagination (default: limit=50, offset=0).

#### 5. `GET /api/checkins/{checkin_id}`

Get full check-in detail including guest list.

**Response 200:** Checkin object (including contact_name, contact_phone) with nested `guests` array.

**Error responses:**
- `404` — Checkin not found

### Removed Endpoints

- `POST /api/documents` — replaced by `POST /api/checkins`
- `GET /api/documents` — replaced by `GET /api/checkins`
- `GET /api/documents/{doc_id}` — replaced by `GET /api/checkins/{checkin_id}`

### Retained Endpoints

- `GET /api/health` — unchanged
- `POST /api/ocr/extract` — kept for internal use by batch-extract
- `POST /api/upload` + `GET /api/upload/files/{filename}` — unchanged

---

## Frontend

### Tab Changes

- **Tab "Scan" (Quet)** → renamed to **"Check-in"** — contains the 3-step wizard
- **Tab "History" (Lich su)** → updated to show check-in records by booking
- **Tab "Info" (Thong tin)** → unchanged

### Wizard UI Structure

```
┌──────────────────────────────────────────────┐
│  Step Indicator:  (1) ──── (2) ──── (3)      │
│                  Booking  Giay to   Xac nhan │
├──────────────────────────────────────────────┤
│                                              │
│         [Step content area]                  │
│                                              │
├──────────────────────────────────────────────┤
│  [← Quay lai]              [Tiep tuc →]      │
└──────────────────────────────────────────────┘
```

### Step 1: Upload Booking Confirmation

- Upload zone (reuse existing component style): camera or gallery
- On upload: call `POST /api/ocr/booking` → show loading spinner
- Display extracted fields as editable inputs:
  - Booking Code (text)
  - Room Type (text)
  - Number of Guests (number)
  - Arrival Date (text, DD/MM/YYYY)
  - Departure Date (text, DD/MM/YYYY)
- "Tiep tuc" button → validate required fields → move to step 2

### Step 2: Upload Identity Documents

- Upload zone with `multiple` attribute — select many images at once
- On upload: call `POST /api/ocr/batch-extract` → show loading with progress
- Display results as guest cards, each showing: name, ID number, document type
- Each card has a delete button (remove from list)
- "Them anh" button to upload additional images (results merge with existing)
- Guest count comparison: show warning banner if `guests.length !== num_guests` from step 1
- "Quay lai" button → step 1 (booking data preserved)
- "Tiep tuc" button → step 3

### Step 3: Review & Confirm

- **Booking section**: read-only summary (code, room type, dates, num_guests)
- **Contact section**: editable fields for contact person:
  - Contact Name (text, required)
  - Contact Phone (text, required)
- **Guest section**: list of guest cards with editable fields:
  - Full Name, Gender (dropdown), Date of Birth, ID Number, Address, Document Type, Nationality
- "Quay lai" button → step 2 (all data preserved)
- "Xac nhan check-in" button → validate contact fields → call `POST /api/checkins` → show success message → reset wizard

### State Management

```javascript
let wizardState = {
  currentStep: 1,
  booking: {
    booking_code: null,
    room_type: null,
    num_guests: null,
    arrival_date: null,
    departure_date: null
  },
  contact: {
    name: null,
    phone: null
  },
  guests: [
    // Each: { full_name, gender, date_of_birth, identification_number, address, document_type, nationality }
  ]
};
```

Navigation between steps preserves all data in `wizardState`. Only "Xac nhan" submission or explicit reset clears the state.

### History Tab (Updated)

- List view: each item shows booking_code, room_type, arrival → departure dates, guest count, status
- On tap: open bottom sheet with full detail:
  - Booking info section
  - Guest list (name, ID number, document type per guest)
- Data from `GET /api/checkins` and `GET /api/checkins/{id}`

---

## OCR Service Changes

### New: `extract_booking_info_async(image_path)`

Uses GPT-5.1 vision API to extract booking information from any confirmation image format.

**Prompt strategy:** Instruct the model to find and extract: booking/reservation code, room type, number of guests, check-in date, check-out date. Return as JSON. Handle any language, any format (screenshot, paper, email).

**Returns:** `{ booking_code, room_type, num_guests, arrival_date, departure_date }`

### New: `batch_extract_info_async(image_paths)`

Processes multiple identity document images and merges results.

**Logic:**
1. For each image, call existing `process_document()`
2. Collect all results into a list
3. Group by `identification_number`
4. For each group, merge: non-null fields from later extractions fill in null fields from earlier ones
5. Return deduplicated guest list

### Existing: `process_document()`

No changes. Continue to handle CCCD, CMND, passport, birth certificate, VNeID screenshots. The existing orientation detection + front/back extraction pipeline already supports these.

---

## File Changes Summary

### New Files
- `database/003_checkin_wizard.sql` — migration script
- `backend/app/models/checkin.py` — Checkin + Guest SQLAlchemy models
- `backend/app/schemas/checkin.py` — Pydantic schemas for checkin API
- `backend/app/api/routes/checkins.py` — checkin CRUD endpoints

### Modified Files
- `backend/app/services/ocr_service.py` — add `extract_booking_info_async()`, `batch_extract_info_async()`
- `backend/app/api/routes/ocr.py` — add `/ocr/booking` and `/ocr/batch-extract` endpoints
- `backend/app/api/routes/__init__.py` — register new routes, remove document routes
- `backend/app/db/base.py` — import new models
- `frontend/index.html` — replace scan tab content with wizard HTML
- `frontend/js/app.js` — wizard state management, step navigation, new API calls
- `frontend/js/api.js` — add new API helper functions
- `frontend/css/style.css` — wizard step indicator, guest cards, warning banner styles

### Removed/Deprecated
- `backend/app/api/routes/documents.py` — replaced by checkins.py
- `backend/app/models/document.py` — replaced by checkin.py
- `backend/app/schemas/document.py` — replaced by checkin.py
- `database/002_documents.sql` — superseded by 003
