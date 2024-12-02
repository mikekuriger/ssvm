"""
Django settings for myproject project.

Generated by 'django-admin startproject' using Django 5.1.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path
import os
import ldap
from django_auth_ldap.config import LDAPSearch, LDAPSearchUnion, GroupOfNamesType, ActiveDirectoryGroupType

# uncomment to import your scheduled tasks, then re-comment it out
SCHEDULER_AUTOSTART = True
MAX_RUN_TIME = 3600

SITE_URL = 'https://ssvm.corp.pvt'

CSRF_TRUSTED_ORIGINS = [
    'https://ssvm.corp.pvt',
    'https://st1lndssvm01.corp.pvt',  # Original server
    'https://st1lndssvm02.corp.pvt',
    'https://st1lnpssvm01.corp.pvt',
    'https://st1lnpssvm02.corp.pvt'
]
# ssl stuff (ssl is configured in nginx)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000  # 1 year
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'  # Define the media URL path

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-ibho6#$u)=+o3l=hvh3sqd9+wjc+8l)(*6l%6powc7$9ajq$ig"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

DEFAULT_FROM_EMAIL = 'SSVM <ssvm@st1lndssvm01.corp.pvt>'

ALLOWED_HOSTS = ['*']

LOGIN_REDIRECT_URL = '/create_vm'

# Application definition

INSTALLED_APPS = [
    'myapp',
    'rest_framework',
    'debug_toolbar',
    'background_task',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myproject.urls"

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

WSGI_APPLICATION = "myproject.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'ssvm',
        'USER': 'ssvm',
        'PASSWORD': 'pay4ssvm',
        'HOST': 'localhost',  # Or your DB server's IP
        'PORT': '3306',
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {'min_length': 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# YP AD for now, will use OKTA or thryv AD if available
AUTH_LDAP_SERVER_URI = "ldap://ca01-ldap.corp.yp.com:389"
AUTH_LDAP_BIND_DN = "CN=s98866,OU=Service Accounts,OU=System Accounts,DC=corp,DC=yp,DC=com"
AUTH_LDAP_BIND_PASSWORD = "P@win-12771"

AUTH_LDAP_USER_SEARCH = LDAPSearchUnion(
    LDAPSearch("OU=Employees,OU=People,DC=corp,DC=yp,DC=com", ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"),
    LDAPSearch("OU=Dex,OU=People,DC=corp,DC=yp,DC=com", ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"),
    LDAPSearch("OU=Dex,OU=Contractors,DC=corp,DC=yp,DC=com", ldap.SCOPE_SUBTREE, "(sAMAccountName=%(user)s)"),
)

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "OU=Employees,OU=People,DC=corp,DC=yp,DC=com",
    ldap.SCOPE_SUBTREE,
    #"(objectCategory=person)"
    "(sAMAccountName=%(user)s)"
)

# Use the `sAMAccountName` attribute as the username
AUTH_LDAP_USER_ATTR_MAP = {
    "username": "sAMAccountName",
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
}

# Optional: to set default staff/superuser status
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_staff": "CN=UnixSysAdmins,OU=Roles,OU=Groups,DC=corp,DC=yp,DC=com",
    #"is_superuser": "CN=UnixSysAdmins,OU=Roles,OU=Groups,DC=corp,DC=yp,DC=com",
}

AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    "OU=Groups,DC=corp,DC=yp,DC=com",
    ldap.SCOPE_SUBTREE,
    "(objectClass=group)"
)


AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType()
AUTH_LDAP_REQUIRE_GROUP = None


# Cache groups for performance
AUTH_LDAP_CACHE_TIMEOUT = 3600
# OU=Employees,OU=People,DC=corp,DC=yp,DC=com?sAMAccountName?sub?(objectCategory=person)"

AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
]



# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = 'America/Chicago'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = "/home/ssvm/ssvm/staticfiles"

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'djangofile': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'ldapfile': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'ldap.log'),
            'formatter': 'verbose',
        },
        'deployfile': {
            'level': 'DEBUG',  # Adjusted to capture DEBUG logs
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'deployment.log'),
            'formatter': 'verbose',
        },
        'destroyfile': {
            'level': 'DEBUG',  # Adjusted to capture DEBUG logs
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'destroy.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['djangofile'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.security.Authentication': {
            'handlers': ['ldapfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django_auth_ldap': {
            'handlers': ['ldapfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['djangofile'],
            'level': 'ERROR',
            'propagate': True,
        },
        'deployment': {
            'handlers': ['deployfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'destroy': {
            'handlers': ['destroyfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


