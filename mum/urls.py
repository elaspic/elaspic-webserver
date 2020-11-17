from django.conf.urls import include, url

urlpatterns = [
    url(r"^", include("web_pipeline.urls")),  # NOTE: without $
]
