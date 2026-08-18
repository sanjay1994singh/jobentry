# Harinam Paper

Django project scaffolded for Python 3.7, based on the `book_patrika` reference project.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Main apps:

- `core`
- `job_entry`
