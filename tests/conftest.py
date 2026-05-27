"""
Fixtures compartidas para todos los tests.
"""

import pytest
from fastapi.testclient import TestClient

# Importar la app de FastAPI
import sys
import os

# Agregar app/ al path para que Python encuentre main.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    """Cliente HTTP de prueba que habla directo con FastAPI (sin Docker)."""
    return TestClient(app)
