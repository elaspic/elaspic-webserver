import pytest
from django.test.client import RequestFactory

from web_pipeline import views


@pytest.mark.django_db
def test_display_result(benchmark):
    rf = RequestFactory()
    request = rf.get("/result/oncokb/")
    response = benchmark(views.displayResult, request)
    assert response
