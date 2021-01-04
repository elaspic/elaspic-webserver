import json
import logging

import pytest
from django.http import Http404, HttpRequest, HttpResponse

from web_pipeline.views_json import getdownloads


def _get_bad_requests():
    requests = []
    request = HttpRequest()
    requests.append(request)
    request = HttpRequest()
    request.GET["m"] = "something"
    requests.append(request)
    request = HttpRequest()
    request.GET["j"] = "something"
    requests.append(request)
    return requests


@pytest.mark.parametrize("http_request", _get_bad_requests())
def test_downloads_error(http_request):
    request = HttpRequest()
    with pytest.raises(Http404):
        _ = getdownloads(request)


def test_getdownloads_noerror(caplog):
    caplog.set_level(logging.ERROR)

    response_data_exp = {
        "simpleresults": [1, 277],
        "allresults": [1, 2643],
        "wtmodelsori": [1, 66015],
        "wtmodelsopt": [1, 46910],
        "mutmodels": [1, 46565],
        "alignments": [1, 498],
        "sequences": [1, 255],
    }

    request = HttpRequest()
    request.GET["j"] = "66018a5f"
    request.GET["m"] = "3eqs.pdb.K39G"
    request.GET["_"] = "1609707160346"

    response = getdownloads(request)
    response_data = json.loads(response.content.decode("utf-8"))
    assert response_data == response_data_exp

    # Examples of errors that could be encountered are:
    # - web_pipeline.models.ProteinLocal.MultipleObjectsReturned
    for record in caplog.records:
        assert record.levelname != "ERROR"
    assert isinstance(response, HttpResponse)
