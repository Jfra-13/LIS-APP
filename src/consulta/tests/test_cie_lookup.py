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
def test_cie_search_prioriza_colera():
    results = search("colera", limit=5)

    assert results
    assert results[0]["code"] == "A00"
    assert results[0]["short_description"] == "Cólera"


@pytest.mark.django_db
def test_cie_search_prioriza_sepsis():
    results = search("sepsis", limit=5)

    assert results
    assert results[0]["code"] == "A41"


@pytest.mark.django_db
def test_cie_endpoint_devuelve_top5(client):
    user = make_user("medico3")
    client.login(username="medico3", password="p")

    response = client.get(reverse("consulta:cie_suggest"), {"q": "colera"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] <= 5
    assert payload["results"]
    assert payload["results"][0]["code"] == "A00"

