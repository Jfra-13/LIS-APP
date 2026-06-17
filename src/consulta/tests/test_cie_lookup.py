import pytest
from django.urls import reverse

from core.models import User
from consulta.services.cie_lookup import search


def make_user(username: str) -> User:
    user = User(username=username)
    user.set_password("p")
    user.save()
    return user



@pytest.mark.django_db
def test_cie_search_prioriza_resfriado():
    results = search("resfriado", limit=5)

    assert results
    assert results[0]["code"] == "J00"
    assert results[0]["short_description"] == "Resfriado común"


@pytest.mark.django_db
def test_cie_search_prioriza_gastritis():
    results = search("gastritis", limit=5)

    assert results
    assert results[0]["code"] == "K29"


@pytest.mark.django_db
def test_cie_endpoint_devuelve_top5(client):
    user = make_user("medico3")
    client.login(username="medico3", password="p")

    response = client.get(reverse("consulta:cie_suggest"), {"q": "cefalea"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] <= 5
    assert payload["results"]
    assert payload["results"][0]["code"] == "R51"

