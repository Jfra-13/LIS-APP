import json
from pathlib import Path


# Fixture JSON para crear grupos iniciales
FIXTURE_DATA = [
    {
        "model": "auth.group",
        "pk": 1,
        "fields": {
            "name": "Tecnicos_Administrativos",
            "permissions": []
        }
    },
    {
        "model": "auth.group",
        "pk": 2,
        "fields": {
            "name": "Enfermeria",
            "permissions": []
        }
    },
    {
        "model": "auth.group",
        "pk": 3,
        "fields": {
            "name": "Medicos_Especialistas",
            "permissions": []
        }
    }
]

def create_fixture():
    """Crear archivo de fixture JSON."""
    fixture_path = Path(__file__).parent / 'fixtures' / 'initial_groups.json'
    fixture_path.parent.mkdir(parents=True, exist_ok=True)

    with open(fixture_path, 'w', encoding='utf-8') as f:
        json.dump(FIXTURE_DATA, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    create_fixture()
    print("Fixture creada en src/admision/fixtures/initial_groups.json")

