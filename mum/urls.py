from django.urls import include, path

urlpatterns = [
    path("", include("web_pipeline.urls")),  # NOTE: without $
]
