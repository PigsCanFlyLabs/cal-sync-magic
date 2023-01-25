import os

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "cal_sync_magic",
    "testapp",
]
SITE_ID = 1

ROOT_URLCONF = "testapp.urls"

DEBUG = True

STATIC_URL = "/static/"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(os.path.dirname(__file__), "database.db"),
    }
}

GOOGLE_CLIENT_SECRETS_FILE = os.getenv(
    "GOOGLE_CLIENT_SECRETS_FILE",
    "client_secret.json")

# If we don't have a secret file but we have the text make it.
if not os.path.exists(GOOGLE_CLIENT_SECRETS_FILE):
    try:
        import json
        print(f"Farts: {os.getenv('FARTS')}")
        secret = os.getenv("GOOGLE_CLIENT_SECRETS_TEXT")
        farts = json.loads(secret)
        assert "web" in farts
        with open(GOOGLE_CLIENT_SECRETS_FILE, 'w') as f:
            f.write(secret)
        print(f"Success! Wrote {GOOGLE_CLIENT_SECRETS_FILE}")
    except Exception as e:
        raise Exception(f"Error writing out secret {e}")

AUTHENTICATION_BACKENDS =  ['django.contrib.auth.backends.ModelBackend']

SECRET_KEY = "donotusethiskey"

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SERVER_NAME = 'localhost'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        }
        }]
