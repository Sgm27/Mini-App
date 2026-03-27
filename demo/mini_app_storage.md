# Mini App Storage API

API cho phep mini app tuong tac voi **Database Storage** (MongoDB) va **Folder Storage** (filesystem).


## Authentication

JWT token (Bearer) la optional. Backend se:

1. Neu mini app la **public** hoac thuoc **public group** → cho phep truy cap khong can JWT
2. Neu mini app la private → yeu cau JWT, verify user co quyen truy cap (owner / group / short_link_access)
3. Verify mini app `config` cho phep truy cap storage tuong ung

## Mini App Config

Khi tao/update mini app, them vao field `config`:

```json
{
  "database_storage_ids": [1, 5],
  "folder_storage_ids": [3, 7]
}
```

---

## Database Storage API

Base URL: `/api/app/{uid}/db`

### List accessible database storages

```
GET /api/app/{uid}/db
```

**Response:**
```json
[
  { "id": 1, "name": "orders", "description": "Order data", "user_id": 10 },
  { "id": 5, "name": "products", "description": null, "user_id": 10 }
]
```

---

### Find documents

```
POST /api/app/{uid}/db/{storage_id}/find
```

**Body:**
```json
{
  "query": { "status": "active" },
  "projection": { "name": 1, "email": 1 },
  "sort": [["created_at", -1]],
  "limit": 20,
  "skip": 0
}
```

**Response:**
```json
{
  "documents": [
    { "_id": "665a...", "name": "John", "email": "john@example.com" }
  ],
  "total": 150
}
```

---

### Insert documents

```
POST /api/app/{uid}/db/{storage_id}/insert
```

**Body (single):**
```json
{
  "documents": { "name": "John", "email": "john@example.com" }
}
```

**Body (multiple):**
```json
{
  "documents": [
    { "name": "John", "email": "john@example.com" },
    { "name": "Jane", "email": "jane@example.com" }
  ]
}
```

**Response (single):**
```json
{ "inserted_id": "665a..." }
```

**Response (multiple):**
```json
{ "inserted_ids": ["665a...", "665b..."] }
```

---

### Update documents

```
PUT /api/app/{uid}/db/{storage_id}/update
```

**Body:**
```json
{
  "filter": { "status": "draft" },
  "update": { "$set": { "status": "published" } },
  "many": true
}
```

**Response:**
```json
{ "matched_count": 5, "modified_count": 5 }
```

---

### Delete documents

```
POST /api/app/{uid}/db/{storage_id}/delete
```

**Body:**
```json
{
  "filter": { "_id": "665a..." },
  "many": false
}
```

**Response:**
```json
{ "deleted_count": 1 }
```

---

### Aggregate

```
POST /api/app/{uid}/db/{storage_id}/aggregate
```

**Body:**
```json
{
  "pipeline": [
    { "$match": { "status": "active" } },
    { "$group": { "_id": "$category", "count": { "$sum": 1 } } }
  ]
}
```

**Response:**
```json
{
  "results": [
    { "_id": "electronics", "count": 42 },
    { "_id": "books", "count": 15 }
  ]
}
```

---

### Count documents

```
POST /api/app/{uid}/db/{storage_id}/count
```

**Body:**
```json
{
  "query": { "status": "active" }
}
```

**Response:**
```json
{ "count": 150 }
```

---

### Get all records

```
GET /api/app/{uid}/db/{storage_id}/all
```

**Response:**
```json
{
  "documents": [...],
  "total": 500
}
```

---

### Create index

```
POST /api/app/{uid}/db/{storage_id}/index
```

**Body:**
```json
{
  "keys": [["email", 1]],
  "unique": true
}
```

**Response:**
```json
{ "index_name": "email_1" }
```

---

## Folder Storage API

Base URL: `/api/app/{uid}/folder`

### List accessible folder storages

```
GET /api/app/{uid}/folder
```

**Response:**
```json
[
  { "id": 3, "name": "reports", "type": "folder", "last_modified": 1711440000 },
  { "id": 7, "name": "uploads", "type": "folder", "last_modified": 1711430000 }
]
```

---

### List folder contents

```
GET /api/app/{uid}/folder?folder_name=reports&directory=2024/march
```

**Response:**
```json
{
  "directory": "reports/2024/march",
  "children": [
    { "name": "report.pdf", "type": "file", "size": 204800, "last_modified": 1711440000 },
    { "name": "images", "type": "folder", "size": 0, "last_modified": 1711430000, "directory": "reports/2024/march/images" }
  ]
}
```

---

### Folder actions (create / delete / rename / copy / move)

```
POST /api/app/{uid}/folder/action
```

#### Create folder
```json
{
  "folder_name": "reports",
  "action": "create",
  "name": "april",
  "directory": "2024"
}
```

#### Delete files/folders
```json
{
  "folder_name": "reports",
  "action": "delete",
  "sources": ["2024/march/old_report.pdf", "2024/march/temp"],
  "directory": "2024/march"
}
```

#### Rename
```json
{
  "folder_name": "reports",
  "action": "rename",
  "source": "2024/march/draft.pdf",
  "new_name": "final.pdf",
  "directory": "2024/march"
}
```

#### Copy
```json
{
  "folder_name": "reports",
  "action": "copy",
  "sources": ["2024/march/report.pdf"],
  "destination": "2024/april"
}
```

#### Move
```json
{
  "folder_name": "reports",
  "action": "move",
  "sources": ["2024/march/report.pdf"],
  "destination": "2024/april"
}
```

**Response (all actions):** Returns updated directory listing.

---

### Upload files

```
POST /api/app/{uid}/folder/upload
Content-Type: multipart/form-data
```

**Form fields:**
- `folder_name` (required): Ten folder storage
- `directory` (optional): Subdirectory path
- `file1`, `file2`, ... : Files to upload

**Response:** Updated directory listing.

---

### Download files

```
POST /api/app/{uid}/folder/download
```

**Body:**
```json
{
  "folder_name": "reports",
  "sources": ["2024/march/report.pdf"]
}
```

**Response (single file):** Short link URL string.

**Response (multiple files):** Short link URL to ZIP file.

---

### Review file content

```
POST /api/app/{uid}/folder/review
```

**Body:**
```json
{
  "folder_name": "reports",
  "source": "2024/march/data.csv",
  "max_lines": 100,
  "offset": 0
}
```

**Response:**
```json
{
  "name": "data.csv",
  "content": "col1,col2\nval1,val2\n...",
  "size": 2048,
  "encoding": "utf-8",
  "extension": ".csv",
  "total_lines": 500,
  "truncated": true
}
```

---

### Save file content

```
POST /api/app/{uid}/folder/save
```

**Body:**
```json
{
  "folder_name": "reports",
  "path": "2024/march/notes.txt",
  "content": "Updated content here..."
}
```

**Response:**
```json
{ "message": "File saved successfully.", "path": "2024/march/notes.txt" }
```

---

## Error Responses

Tat ca endpoints tra ve HTTP error voi format:

```json
{ "detail": "Error message here" }
```

| Status | Mo ta |
|--------|-------|
| 400 | Bad request / missing params |
| 401 | Chua dang nhap |
| 403 | Khong co quyen truy cap mini app hoac storage |
| 404 | Mini app / storage / file not found |
| 500 | Server error |
