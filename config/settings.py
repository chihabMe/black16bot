"""Django settings for the Black16 Telegram shop bot."""

import os
from pathlib import Path
from urllib.parse import urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


def database_from_url(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must use postgres:// or postgresql://")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "localhost",
        "PORT": parsed.port or 5432,
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
    }


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")

DEBUG = env_bool("DJANGO_DEBUG", True)

if not DEBUG and SECRET_KEY == "dev-only-change-me":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'catalog',
    'wallet',
    'orders',
    'payments',
    'support',
    'broadcasts',
    'api_access',
    'audit',
    'bot',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.RequestIDMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://black16bot:black16bot@localhost:5432/black16bot",
)

DATABASES = {"default": database_from_url(DATABASE_URL)}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.getenv("TIME_ZONE", "UTC")

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_IDS = {
    int(value)
    for value in env_list("TELEGRAM_ADMIN_IDS")
    if value.lstrip("-").isdigit()
}
DEFAULT_BOT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "USDT")
DEVELOPER_API_ENABLED = env_bool("DEVELOPER_API_ENABLED", True)
TELEGRAM_ACCOUNTS_ENABLED = env_bool("TELEGRAM_ACCOUNTS_ENABLED", True)
REFERRAL_FEATURE_ENABLED = env_bool("REFERRAL_FEATURE_ENABLED", True)
REFERRAL_COMMISSION_RATE = os.getenv("REFERRAL_COMMISSION_RATE", "0.05")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", os.getenv("BINANCE_PAY_API_KEY", ""))
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", os.getenv("BINANCE_PAY_API_SECRET", ""))
BINANCE_API_BASE_URL = os.getenv("BINANCE_API_BASE_URL", "https://api.binance.com")
BINANCE_PAY_ID = os.getenv("BINANCE_PAY_ID", "")
BINANCE_PAY_UID = os.getenv("BINANCE_PAY_UID", "")
BYBIT_PAY_ID = os.getenv("BYBIT_PAY_ID", "")
USDT_BEP20_WALLET_ADDRESS = os.getenv("USDT_BEP20_WALLET_ADDRESS", "")
USDT_TRC20_WALLET_ADDRESS = os.getenv("USDT_TRC20_WALLET_ADDRESS", "")
BSCSCAN_API_BASE_URL = os.getenv("BSCSCAN_API_BASE_URL", "https://api.etherscan.io/v2/api")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
BSC_CHAIN_ID = os.getenv("BSC_CHAIN_ID", "56")
BSC_USDT_CONTRACT_ADDRESS = os.getenv("BSC_USDT_CONTRACT_ADDRESS", "0x55d398326f99059ff775485246999027b3197955")
BSC_MIN_CONFIRMATIONS = int(os.getenv("BSC_MIN_CONFIRMATIONS", "15"))
MORALIS_API_BASE_URL = os.getenv("MORALIS_API_BASE_URL", "https://deep-index.moralis.io/api/v2.2")
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY", "")
TRONGRID_API_BASE_URL = os.getenv("TRONGRID_API_BASE_URL", "https://api.trongrid.io")
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "")
TRON_USDT_CONTRACT_ADDRESS = os.getenv("TRON_USDT_CONTRACT_ADDRESS", "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj")
SUPPORT_TELEGRAM_USERNAME = os.getenv("SUPPORT_TELEGRAM_USERNAME", "")
SUPPORT_CHANNEL_URL = os.getenv("SUPPORT_CHANNEL_URL", "")
PUBLIC_CHANNEL_URL = os.getenv("PUBLIC_CHANNEL_URL", "")
ADMIN_NOTIFICATION_CHAT_ID = os.getenv("ADMIN_NOTIFICATION_CHAT_ID", "")
API_KEY_PEPPER = os.getenv("API_KEY_PEPPER", SECRET_KEY)
WEBHOOK_SIGNING_SECRET = os.getenv("WEBHOOK_SIGNING_SECRET", SECRET_KEY)
STOCK_ENCRYPTION_KEY = os.getenv("STOCK_ENCRYPTION_KEY", SECRET_KEY)

if not DEBUG and WEBHOOK_SIGNING_SECRET == SECRET_KEY:
    raise ImproperlyConfigured("WEBHOOK_SIGNING_SECRET must be separate from DJANGO_SECRET_KEY in production.")

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Logging configuration

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s %(user_id)s',
        },
    },
    'filters': {
        'request_context': {
            '()': 'core.logging.RequestContextFilter',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if DEBUG else 'json',
            'filters': ['request_context'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'bot': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'payments': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'orders': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
