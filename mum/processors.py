from django.conf import settings


def sitevars(HttpRequest):
    return {'SITE_NAME': settings.SITE_NAME,
            'STATIC_FOLDER': settings.STATIC_URL,
            'MEDIA_FOLDER': settings.MEDIA_URL,
            'JOB_EXPIRY_DAY': settings.JOB_EXPIRY_DAY,
            'TIME_LIMIT': settings.TASK_SOFT_TIME_LIMIT / 3600}
