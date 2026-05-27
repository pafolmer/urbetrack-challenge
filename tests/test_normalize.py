"""
Property test: Key-order independence of normalization.

Property 4: Para cualquier objeto JSON (incluyendo anidados),
normalizar debe producir output idéntico sin importar el orden
original de claves en cualquier nivel.

Validates: Requirements 10.1, 10.3
"""

import json
import random

from hypothesis import given, settings
from hypothesis import strategies as st

# Importar la función de normalización de la app
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from main import normalize_json  # noqa: E402


def shuffle_dict(d):
    """Reordena las claves de un dict (y sub-dicts) aleatoriamente."""
    if isinstance(d, dict):
        items = list(d.items())
        random.shuffle(items)
        return {k: shuffle_dict(v) for k, v in items}
    elif isinstance(d, list):
        return [shuffle_dict(item) for item in d]
    return d


# Estrategia para generar dicts anidados
nested_dicts = st.recursive(
    st.one_of(
        st.text(max_size=20),
        st.integers(min_value=-1000, max_value=1000),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.none(),
    ),
    lambda children: st.one_of(
        st.lists(children, max_size=3),
        st.dictionaries(st.text(min_size=1, max_size=8), children, min_size=1, max_size=4),
    ),
    max_leaves=15,
)


@given(data=st.dictionaries(st.text(min_size=1, max_size=8), nested_dicts, min_size=1, max_size=4))
@settings(max_examples=100)
def test_key_order_independence(data):
    """
    Property 4: Key-order independence.

    Normalizar un dict y luego normalizar el mismo dict con claves
    desordenadas debe producir exactamente el mismo string.
    """
    # Normalizar el original
    normalized_original = normalize_json(data)

    # Desordenar las claves y normalizar de nuevo
    shuffled = shuffle_dict(data)
    normalized_shuffled = normalize_json(shuffled)

    # Deben ser idénticos
    assert normalized_original == normalized_shuffled
