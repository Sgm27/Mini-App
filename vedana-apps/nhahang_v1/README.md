# Full Stack Template (HTML/CSS/JS)

Template cho việc tạo full stack web application với pure HTML/CSS/JavaScript.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML5 + CSS3 + Vanilla JavaScript (ES6+) |
| Backend | FastAPI + Python + SQLAlchemy |
| Database | SQLite (default) / PostgreSQL |

## Cấu trúc

```
project/
├── frontend/           # Static frontend
│   ├── index.html      # Main HTML entry
│   ├── css/
│   │   └── style.css   # Stylesheet
│   ├── js/
│   │   ├── api.js      # API helper (fetch wrapper)
│   │   └── app.js      # Main app logic
│   └── assets/         # Images, fonts
├── backend/            # FastAPI application
│   ├── app/
│   │   ├── api/routes/ # API endpoints
│   │   ├── core/       # Config
│   │   ├── db/         # Database
│   │   ├── models/     # SQLAlchemy models
│   │   ├── schemas/    # Pydantic schemas
│   │   └── services/   # Business logic
│   └── requirements.txt
└── database/           # SQL migrations
    └── 001_init.sql
```

## Cách sử dụng

### 1. Chạy Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 2701
```

Backend chạy tại: http://localhost:2701
- API docs: http://localhost:2701/docs
- Health check: http://localhost:2701/api/health

### 2. Chạy Frontend

```bash
cd frontend
python -m http.server 8386
```

Frontend chạy tại: http://localhost:8386

## Cấu hình

### Backend (.env)

```env
PROJECT_NAME=My App
VERSION=1.0.0
API_HOST=0.0.0.0
API_PORT=2701
DATABASE_URL=sqlite:///./app.db
```

### Frontend

Sửa `API_BASE_URL` trong `js/api.js`:

```javascript
const API_BASE_URL = 'http://localhost:2701';
```

## Tính năng có sẵn

### Frontend
- CSS responsive với media queries
- CSS variables cho theming
- Fetch API wrapper (GET/POST/PUT/DELETE)
- Form validation helpers
- Loading/Error/Empty states
- Utility classes (btn, card, form-*, table, etc.)

### Backend
- CORS enabled
- Health check endpoint
- SQLAlchemy ORM
- Pydantic validation
- Auto-reload in development

## Thêm API mới

### 1. Tạo route

```python
# backend/app/api/routes/users.py
from fastapi import APIRouter

router = APIRouter(prefix="/users")

@router.get("/")
async def get_users():
    return [{"id": 1, "name": "John"}]
```

### 2. Đăng ký route

```python
# backend/app/api/routes/__init__.py
from app.api.routes import health, users

def register_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(users.router, tags=["users"])
    app.include_router(api_router)
```

## Gọi API từ Frontend

```javascript
// Sử dụng api.js
async function loadUsers() {
    const container = document.getElementById('users');
    showLoading(container);

    try {
        const users = await api.get('/api/users');
        if (users.length === 0) {
            showEmpty(container, 'No users found');
            return;
        }
        container.innerHTML = users.map(u => `
            <div class="card">
                <h3 class="card-title">${escapeHtml(u.name)}</h3>
            </div>
        `).join('');
    } catch (error) {
        showError(container, error.message);
    }
}
```

## Fixed Ports

- Frontend: **8386**
- Backend: **2701**
