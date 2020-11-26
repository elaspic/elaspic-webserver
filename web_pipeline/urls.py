from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path, re_path

from . import views, views_json

# admin.autodiscover()

urlpatterns = []

# Views accessed directly by the user.
urlpatterns += [
    # Input sites.
    path("", views.inp, {"p": "sIn"}),
    path("many/", views.inp, {"p": "mIn"}),
    path("run/", views.runPipeline),
    # Results sites.
    re_path(r"^result/[a-zA-Z0-9]{6,12}/$", views.displayResult),
    re_path(
        r"^result/[a-zA-Z0-9]{6,12}/.+\.[A-Za-z]{1}[0-9]+[A-Za-z]{1}/$",
        views.displaySecondaryResult,
    ),
    path("popup/jsmol/", views.jsmolpopup),
    # Generic sites.
    re_path(r"^(help|reference|contact)/$", views.genericSite),
]

# Views accessed through AJAX calls.
urlpatterns += [
    # Input sites.
    path("json/getprotein/", views_json.getProtein),
    path("json/uploadfile/", views_json.uploadFile),
    # Results sites.
    path("json/checkjob/", views_json.checkIfJobIsReady),
    path("json/rerun/", views_json.rerunMut),
    path("getfile/", views_json.getfile),
    path("json/getdownloads/", views_json.getdownloads),
    # Generic.
    path("json/contactmail/", views_json.contactmail),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
