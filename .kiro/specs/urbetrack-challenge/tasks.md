# Implementation Plan: Urbetrack MD5 Validator Challenge

## Overview

Implementación incremental del challenge DevOps/SRE: API REST (Python 3.12 + FastAPI) → Dockerfile → Nginx reverse proxy → Docker Compose → Scripts Bash → CI Pipeline → Property Tests → README. Cada paso construye sobre el anterior, sin código huérfano.

## Tasks

- [ ] 1. Implementar API REST con FastAPI
  - [x] 1.1 Crear estructura base del proyecto y dependencias
    - Crear `app/requirements.txt` con FastAPI, uvicorn, pydantic (versiones pinneadas)
    - Crear `app/__init__.py` vacío si es necesario
    - _Requirements: 1.1, 2.1, 3.1_

  - [x] 1.2 Implementar funciones de normalización y cálculo MD5
    - Implementar `normalize_json(data)` usando `json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`
    - Implementar `compute_md5(normalized)` usando `hashlib.md5(normalized.encode('utf-8')).hexdigest()`
    - _Requirements: 1.1, 10.1, 10.2, 10.3_

  - [ ] 1.3 Implementar endpoint POST /validate-md5
    - Definir modelos Pydantic: `ValidateMD5Request(data: Any, md5: str)`, `ValidateMD5Response(md5: str)`, `ErrorResponse(detail: str)`
    - Implementar lógica: normalizar → calcular MD5 → comparar → 200 o 400
    - Retornar 400 con detalle de mismatch si no coincide
    - FastAPI/Pydantic maneja automáticamente 422 para campos faltantes o JSON inválido
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.4 Implementar endpoint GET /health
    - Retornar `{"status": "healthy"}` con HTTP 200
    - Sin autenticación ni headers requeridos
    - _Requirements: 2.1, 2.2_

  - [ ] 1.5 Configurar metadata OpenAPI/Swagger
    - Configurar `FastAPI(title="Urbetrack MD5 Validator", version="1.0.0")`
    - Agregar `response_model`, `responses`, y ejemplos en los decoradores de endpoints
    - Verificar que `/docs` y `/openapi.json` exponen la especificación correctamente
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 2. Crear Dockerfile optimizado
  - [ ] 2.1 Escribir Dockerfile multi-stage
    - Stage 1 (builder): `python:3.12-slim`, instalar dependencias con `--prefix=/install`
    - Stage 2 (runtime): `python:3.12-slim`, crear usuario non-root `appuser`, copiar deps desde builder, copiar código app
    - Ordenar capas: requirements.txt antes que código de aplicación para cache óptimo
    - `USER appuser`, `EXPOSE 8000`, CMD con uvicorn
    - _Requirements: 4.1, 4.2, 4.4_

  - [ ] 2.2 Agregar HEALTHCHECK nativo y .dockerignore
    - Agregar instrucción `HEALTHCHECK` que valide `/health` con `python -c "import urllib.request; ..."`
    - Crear `.dockerignore` excluyendo `.git`, `__pycache__`, `tests/`, `.github/`, `*.md`
    - _Requirements: 4.3_

- [ ] 3. Configurar Nginx reverse proxy
  - [ ] 3.1 Crear configuración Nginx
    - Crear `nginx/nginx.conf` con upstream `api:8000`
    - Configurar `limit_req_zone` para rate limiting en `/validate-md5` (10r/s, burst=20, nodelay)
    - Configurar `limit_req_status 429`
    - Pasar headers: `X-Forwarded-For`, `X-Real-IP`, `Host`
    - Location `/` y location `/validate-md5` con proxy_pass al upstream
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 4. Crear Docker Compose stack
  - [ ] 4.1 Escribir docker-compose.yml
    - Definir servicio `api`: build desde `.`, conectado a red `internal`, restart `unless-stopped`
    - Definir servicio `nginx`: imagen `nginx:1.25-alpine`, puerto `80:80`, volume mount de nginx.conf, depends_on api (condition: service_healthy)
    - Definir red `internal` con driver bridge
    - NO exponer puerto del contenedor API al host
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 5. Checkpoint - Verificar stack funcional
  - Ensure all tests pass, ask the user if questions arise.
  - Verificar: `docker compose up -d` levanta ambos servicios, `curl http://localhost/health` retorna 200.

- [ ] 6. Crear scripts Bash de automatización
  - [ ] 6.1 Implementar build.sh
    - Shebang `#!/usr/bin/env bash`, `set -euo pipefail`
    - Ejecutar `docker compose build`
    - Exit code non-zero en fallo
    - _Requirements: 7.1, 7.5, 7.6_

  - [ ] 6.2 Implementar start.sh
    - `docker compose up -d`
    - Exit code non-zero en fallo
    - _Requirements: 7.2, 7.5, 7.6_

  - [ ] 6.3 Implementar stop.sh
    - `docker compose down`
    - Exit code non-zero en fallo
    - _Requirements: 7.3, 7.5, 7.6_

  - [ ] 6.4 Implementar healthcheck.sh
    - Loop con `curl -sf http://localhost/health` cada 5 segundos
    - Soportar variable de entorno `MAX_RETRIES` (default: infinito para uso local, configurable para CI)
    - Reportar estado a stdout con timestamp
    - Exit code 1 si el endpoint no responde tras agotar reintentos
    - _Requirements: 7.4, 7.5, 7.6_

  - [ ] 6.5 Implementar dev.sh
    - `docker compose up --build --watch` o equivalente con bind mount + reload
    - Hot-reload habilitado para cambios en código fuente
    - _Requirements: 7.7_

- [ ] 7. Crear pipeline CI con GitHub Actions
  - [ ] 7.1 Escribir workflow .github/workflows/ci.yml
    - Trigger en push
    - Steps: checkout, setup Docker Buildx, cache Docker layers (actions/cache), build con tag SHA del commit
    - `docker compose config` para validación
    - `docker compose up -d`, wait, healthcheck real contra API corriendo
    - Trivy scan con `--exit-code 1` para HIGH/CRITICAL
    - Secrets demo: inyectar variable de entorno simulada desde GitHub Secrets al runtime del contenedor
    - Cleanup con `docker compose down`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 8. Checkpoint - Verificar CI y scripts
  - Ensure all tests pass, ask the user if questions arise.
  - Verificar: scripts ejecutables, CI workflow válido con revisión manual.

- [ ] 9. Implementar tests con Hypothesis y pytest
  - [ ] 9.1 Crear conftest.py con fixtures y generadores
    - Fixture `client` con `TestClient(app)`
    - Generadores Hypothesis para JSON válido (objetos anidados, arrays, primitivos)
    - _Requirements: 10.1_

  - [ ] 9.2 Write property test: Round-trip MD5 validation
    - **Property 1: Round-trip MD5 validation**
    - Para cualquier JSON válido, computar MD5 de su forma normalizada y enviar ambos a POST `/validate-md5` debe retornar HTTP 200 con el mismo hash
    - **Validates: Requirements 1.1, 1.2**

  - [ ]* 9.3 Write property test: Mismatch rejection
    - **Property 2: Mismatch rejection**
    - Para cualquier JSON válido y cualquier MD5 que NO coincida con el MD5 normalizado, POST `/validate-md5` debe retornar error HTTP
    - **Validates: Requirements 1.3**

  - [ ]* 9.4 Write property test: Missing fields rejection
    - **Property 3: Missing fields rejection**
    - Para cualquier payload JSON sin campo `data`, sin campo `md5`, o sin ambos, POST `/validate-md5` debe retornar HTTP 422
    - **Validates: Requirements 1.4**

  - [ ] 9.5 Write property test: Key-order independence
    - **Property 4: Key-order independence of normalization**
    - Para cualquier objeto JSON (incluyendo anidados), normalizar debe producir output idéntico sin importar el orden original de claves
    - **Validates: Requirements 10.1, 10.3**

  - [ ]* 9.6 Write property test: Normalization idempotence
    - **Property 5: Normalization idempotence**
    - Para cualquier objeto JSON, normalizar → parsear → re-normalizar debe producir el mismo hash MD5
    - **Validates: Requirements 10.2**

  - [ ]* 9.7 Write unit tests para /health
    - Test GET /health retorna 200 con `{"status": "healthy"}`
    - Test que no requiere headers ni auth
    - _Requirements: 2.1, 2.2_

- [ ] 10. Crear README con documentación completa
  - [ ] 10.1 Escribir README.md
    - Secciones: descripción, arquitectura, pasos para levantar/detener, ejemplos curl (válidos e inválidos)
    - Explicación del cálculo MD5 con detalles de normalización
    - Decisiones técnicas con justificación
    - Supuestos y limitaciones
    - Sección de mejoras para producción: deployment strategy, rollback, logging, métricas, alertas, secrets management, escalabilidad, security hardening, container registry, image versioning, resource limits
    - _Requirements: 9.1, 9.2_

- [ ] 11. Final checkpoint - Validación completa
  - Ensure all tests pass, ask the user if questions arise.
  - Verificar: todos los archivos creados, docker compose up funcional, healthcheck OK, tests pasan, README completo.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- El orden de implementación garantiza que cada paso tiene sus dependencias resueltas
- Python 3.12 + FastAPI es el stack definido en el diseño; Hypothesis para PBT

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.4"] },
    { "id": 2, "tasks": ["1.3", "1.5"] },
    { "id": 3, "tasks": ["2.1", "3.1"] },
    { "id": 4, "tasks": ["2.2", "4.1"] },
    { "id": 5, "tasks": ["6.1", "6.2", "6.3", "6.4", "6.5"] },
    { "id": 6, "tasks": ["7.1"] },
    { "id": 7, "tasks": ["9.1"] },
    { "id": 8, "tasks": ["9.2", "9.3", "9.4", "9.5", "9.6", "9.7"] },
    { "id": 9, "tasks": ["10.1"] }
  ]
}
```
