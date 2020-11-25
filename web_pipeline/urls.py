from django.conf import settings
from django.conf.urls import url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from . import views, views_json

# admin.autodiscover()

urlpatterns = []

# Views accessed directly by the user.
urlpatterns += [
    # Input sites.
    url(r"^$", views.inp, {"p": "sIn"}),
    url(r"^many/$", views.inp, {"p": "mIn"}),
    url(r"^run/$", views.runPipeline),
    # Results sites.
    url(r"^result/[a-zA-Z0-9]{6,12}/$", views.displayResult),
    url(
        r"^result/[a-zA-Z0-9]{6,12}/.+\.[A-Za-z]{1}[0-9]+[A-Za-z]{1}/$",
        views.displaySecondaryResult,
    ),
    url(r"^popup/jsmol/$", views.jsmolpopup),
    # Generic sites.
    url(r"^(help|reference|contact)/$", views.genericSite),
]

# Views accessed through AJAX calls.
urlpatterns += [
    # Input sites.
    url(r"^json/getprotein/$", views_json.getProtein),
    url(r"^json/uploadfile/$", views_json.uploadFile),
    # Results sites.
    url(r"^json/checkjob/$", views_json.checkIfJobIsReady),
    url(r"^json/rerun/$", views_json.rerunMut),
    url(r"^getfile/", views_json.getfile),
    url(r"^json/getdownloads/$", views_json.getdownloads),
    # Generic.
    url(r"^json/contactmail/$", views_json.contactmail),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
