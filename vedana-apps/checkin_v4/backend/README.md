## FastAPI Backend Template

This template follows a conventional FastAPI project layout so code generation tools can easily reason about the runtime, configuration, and dependency graph.

```
backend/
├── app
│   ├── api
│   │   ├── deps.py
│   │   └── routes
│   │       ├── __init__.py
│   │       └── health.py
│   ├── core
│   │   └── config.py
│   ├── db
│   │   ├── base.py
│   │   ├── base_class.py
│   │   ├── init_db.py
│   │   └── session.py
│   ├── main.py
│   ├── models
│   │   └── __init__.py
│   ├── schemas
│   │   └── __init__.py
│   └── services
│       └── __init__.py
├── requirements.txt
└── README.md
```

### Quick start

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Environment variables

Configuration values live in `app/core/config.py` and default to sensible development values. Override them with environment variables or a `.env` file placed next to `requirements.txt`.

