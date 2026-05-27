"""
Property test: Round-trip MD5 validation.

Property 1: Para cualquier JSON válido, si calculo el MD5 de su forma
normalizada y envío ambos a POST /validate-md5, siempre retorna 200
con el mismo hash.

Validates: Requirements 1.1, 1.2
"""

import hashlib
import json

from hypothesis import given, settings
from hypothesis import strategies as st


# Estrategia para generar JSON válido (dicts con valores variados)
json_values = st.recursive(
    # Valores base: strings, ints, floats, bools, None
    st.one_of(
        st.text(max_size=50),
        st.integers(min_value=-1000, max_value=1000),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.none(),
    ),
    # Recursión: listas y dicts que contienen valores base
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=5),
    ),
    max_leaves=20,
)


@given(data=st.dictionaries(st.text(min_size=1, max_size=10), json_values, min_size=1, max_size=5))
@settings(max_examples=100)
def test_roundtrip_md5_validation(client, data):
    """
    Property 1: Round-trip MD5 validation.

    Si calculo el MD5 correctamente y lo envío junto con los datos,
    la API siempre debe retornar 200 con ese mismo hash.
    """
    # Normalizar igual que la API
    normalized = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected_md5 = hashlib.md5(normalized.encode("utf-8")).hexdigest()

    # Enviar a la API
    response = client.post(
        "/validate-md5",
        json={"data": data, "md5": expected_md5},
    )

    # Siempre debe ser 200 con el hash correcto
    assert response.status_code == 200
    assert response.json()["md5"] == expected_md5
