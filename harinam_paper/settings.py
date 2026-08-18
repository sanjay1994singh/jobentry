import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
IS_FROZEN = getattr(sys, "frozen", False)

SECRET_KEY = "harinam-paper-local-desktop-key"

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "job_entry.apps.JobEntryConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "harinam_paper.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "harinam_paper.wsgi.application"


def default_data_dir():
    env_data_dir = os.getenv("HARINAM_PAPER_DATA_DIR")
    if env_data_dir:
        return Path(env_data_dir)
    if IS_FROZEN:
        root = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
        return Path(root) / "HarinamPress" / "HarinamPaper"
    return BASE_DIR


DATA_DIR = default_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

REPORT_DIR = DATA_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "harinam_paper.sqlite3",
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1",
    "http://localhost",
]
