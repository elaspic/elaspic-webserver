from django.conf.urls import url, include


urlpatterns = [
    url(r'^', include('web_pipeline.urls')),  # NOTE: without $
]
