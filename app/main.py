"""
Urbetrack MD5 Validator API
---------------------------
API REST que valida checksums MD5 de payloads JSON normalizados.
FastAPI genera Swagger/OpenAPI automáticamente en /docs y /openapi.json.
"""

import hashlib
import json
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Crear la aplicación FastAPI.
# title y version se usan para generar la documentación Swagger.
app = FastAPI(
    title="Urbetrack MD5 Validator",
    version="1.0.0",
    description="API para validar integridad de datos JSON mediante checksums MD5",
)


# --- Modelos de datos (schemas de request/response) ---


class ValidateMD5Request(BaseModel):
    """Schema del request para POST /validate-md5."""

    data: Any = Field(..., description="Payload JSON a validar (cualquier JSON válido)")
    md5: str = Field(..., description="Hash MD5 esperado (string de 32 caracteres hex)")

    # Ejemplo que aparece en el Swagger para que el evaluador pruebe fácil
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "data": {"name": "test", "value": 123},
                    "md5": "a]será calculado por el cliente",
                }
            ]
        }
    }


class ValidateMD5Response(BaseModel):
    """Schema del response exitoso (200 OK)."""

    md5: str


class ErrorDetail(BaseModel):
    """Schema del response de error (400 Bad Request)."""

    error: str
    expected: str
    calculated: str


# --- Funciones core de normalización y hash ---


def normalize_json(data: Any) -> str:
    """
    Serializa un objeto Python a JSON canónico determinista.

    - sort_keys=True: ordena claves alfabéticamente en todos los niveles
    - separators=(',', ':'): elimina espacios (formato compacto)
    - ensure_ascii=False: permite caracteres unicode sin escapar

    Ejemplo:
        {"b": 2, "a": 1} → '{"a":1,"b":2}'
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_md5(text: str) -> str:
    """
    Calcula el MD5 hex digest de un string codificado en UTF-8.

    Retorna un string de 32 caracteres hexadecimales.
    usedforsecurity=False indica que MD5 se usa como checksum de integridad,
    no para seguridad criptográfica.
    """
    return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()  # nosec B324


# --- Endpoints ---


@app.post(
    "/validate-md5",
    response_model=ValidateMD5Response,
    responses={
        400: {
            "description": "MD5 no coincide con el contenido",
            "model": ErrorDetail,
        }
    },
)
def validate_md5(payload: ValidateMD5Request):
    """
    Valida que el MD5 provisto corresponda al campo data normalizado.

    Proceso:
    1. Normaliza el campo `data` (sort keys, compact, UTF-8)
    2. Calcula MD5 del string normalizado
    3. Compara con el `md5` provisto por el cliente
    """
    # Paso 1: normalizar el JSON del campo data
    normalized = normalize_json(payload.data)

    # Paso 2: calcular el hash MD5 del string normalizado
    calculated = compute_md5(normalized)

    # Paso 3: comparar con lo que mandó el cliente
    if calculated != payload.md5:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "MD5 mismatch",
                "expected": payload.md5,
                "calculated": calculated,
            },
        )

    # Si llegamos acá, los hashes coinciden → 200 OK
    return ValidateMD5Response(md5=calculated)


@app.get("/health")
def health():
    """Endpoint de health check. Retorna 200 OK si el servicio está disponible."""
    return {"status": "healthy"}
