from django.conf import settings


def sitevars(HttpRequest):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "STATIC_FOLDER": settings.STATIC_URL,
        "MEDIA_FOLDER": settings.MEDIA_URL,
    }
