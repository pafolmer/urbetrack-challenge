# Urbetrack MD5 Validator API

API REST que valida checksums MD5 de payloads JSON normalizados. Containerizada con Docker, fronteada por Nginx como reverse proxy, automatizada con scripts Bash, y validada mediante un pipeline CI de GitHub Actions.

## Arquitectura

```
Cliente HTTP → :8080 Nginx (reverse proxy + rate limiting) → red interna Docker → :8000 FastAPI
```

- **Nginx** escucha en el puerto 8080 del host y reenvía al contenedor de la API.
- **La API** solo es accesible desde la red interna de Docker. No está expuesta al host directamente.
- **Rate limiting** en `/validate-md5` previene abuso por cómputo intensivo de hashes (10 req/s por IP, burst de 20).

## Quick Start

### Requisitos

- Docker Desktop (o Docker Engine + Docker Compose v2)
- Puerto 8080 disponible en el host

### Levantar el entorno

```bash
# Construir imágenes
./scripts/build.sh

# Levantar en background
./scripts/start.sh

# Verificar que está corriendo
curl http://localhost:8080/health
# → {"status":"healthy"}
```

### Detener el entorno

```bash
./scripts/stop.sh
```

### Desarrollo local (hot-reload)

```bash
./scripts/dev.sh
# Editar app/main.py → uvicorn reinicia automáticamente
```

### Monitoreo de salud

```bash
# Loop infinito (Ctrl+C para detener)
./scripts/healthcheck.sh

# Con límite de reintentos (para CI)
MAX_RETRIES=12 ./scripts/healthcheck.sh
```

## Endpoints

### GET /health

Valida disponibilidad del servicio.

```bash
curl http://localhost:8080/health
```

**Response 200:**
```json
{"status": "healthy"}
```

### POST /validate-md5

Valida que el MD5 provisto corresponda al campo `data` normalizado.

**Request válido (hash correcto):**
```bash
curl -X POST http://localhost:8080/validate-md5 \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "test", "value": 123}, "md5": "9acbbd1a1aa279fa26b5a3aab2e39293"}'
```

**Response 200:**
```json
{"md5": "9acbbd1a1aa279fa26b5a3aab2e39293"}
```

**Request inválido (hash incorrecto):**
```bash
curl -X POST http://localhost:8080/validate-md5 \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "test", "value": 123}, "md5": "hash_incorrecto"}'
```

**Response 400:**
```json
{
  "detail": {
    "error": "MD5 mismatch",
    "expected": "hash_incorrecto",
    "calculated": "9acbbd1a1aa279fa26b5a3aab2e39293"
  }
}
```

**Request inválido (campos faltantes):**
```bash
curl -X POST http://localhost:8080/validate-md5 \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "test"}}'
```

**Response 422:**
```json
{
  "detail": [
    {
      "loc": ["body", "md5"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

### Swagger UI

Documentación interactiva disponible en: `http://localhost:8080/docs`

Especificación OpenAPI en JSON: `http://localhost:8080/openapi.json`

## Decisiones Técnicas

### Stack

| Componente | Elección | Justificación |
|-----------|----------|---------------|
| Lenguaje | Python 3.12 | Ecosistema maduro, FastAPI disponible |
| Framework | FastAPI | Auto-genera Swagger/OpenAPI sin config extra, validación con Pydantic, async nativo |
| Servidor WSGI | Uvicorn | Servidor ASGI estándar para FastAPI, soporte async |
| Reverse Proxy | Nginx | Estándar de industria, rate limiting nativo, configuración declarativa |
| Contenedores | Docker + Compose | Orquestación local reproducible, red aislada |
| CI/CD | GitHub Actions | Integración nativa con el repositorio |
| Testing | pytest + Hypothesis | Property-based testing para validar propiedades universales |

### Cálculo del MD5

**Approach elegido:** Campo separado con normalización.

El payload del request tiene la estructura:
```json
{
  "data": { ... },   // Objeto JSON a validar
  "md5": "abc123..." // Hash MD5 esperado
}
```

**Proceso de normalización:**
1. Se toma el campo `data` (cualquier JSON válido)
2. Se serializa con `json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`
   - `sort_keys=True`: ordena claves alfabéticamente en todos los niveles de anidamiento
   - `separators=(',', ':')`: elimina espacios (formato compacto)
   - `ensure_ascii=False`: preserva caracteres unicode
3. Se codifica el string resultante en UTF-8
4. Se calcula `hashlib.md5(encoded_bytes).hexdigest()`

**¿Por qué normalizar?**

JSON no garantiza orden de claves. `{"b":2,"a":1}` y `{"a":1,"b":2}` representan los mismos datos pero producen strings distintos y por lo tanto hashes distintos. La normalización garantiza que los mismos datos lógicos siempre produzcan el mismo hash, independientemente de cómo el cliente los serialice.

**¿Por qué campo separado?**

Separar `data` de `md5` en el payload evita la ambigüedad de "¿hasheo el body completo incluyendo el campo md5?". El cliente sabe exactamente qué se hashea: el campo `data` normalizado.

**Ejemplo de cálculo manual:**
```python
import hashlib, json
data = {"name": "test", "value": 123}
normalized = json.dumps(data, sort_keys=True, separators=(',', ':'))
# → '{"name":"test","value":123}'
md5 = hashlib.md5(normalized.encode('utf-8')).hexdigest()
# → '9acbbd1a1aa279fa26b5a3aab2e39293'
```

### Nginx como Reverse Proxy

- La API no expone puertos al host. Solo Nginx (puerto 8080) es accesible externamente.
- Rate limiting en `/validate-md5` (10 req/s, burst 20) previene DoS por cómputo de hashes.
- Headers de proxy (`X-Real-IP`, `X-Forwarded-For`) permiten a la API conocer la IP real del cliente.

### Dockerfile

- Multi-stage: stage builder instala dependencias, stage runtime solo tiene el código y las libs.
- Non-root user (`appuser`): reduce superficie de ataque.
- HEALTHCHECK nativo: Docker marca el contenedor como unhealthy si `/health` no responde.
- Layer ordering: `requirements.txt` se copia antes que el código para maximizar cache.

## Supuestos y Limitaciones

- **Puerto 8080**: Se usa un puerto no privilegiado para evitar conflictos con servicios existentes en el host.
- **MD5 como checksum**: MD5 está criptográficamente roto para colisiones, pero sigue siendo válido como checksum de integridad (no se usa para seguridad criptográfica).
- **Sin autenticación**: La API no implementa auth. En producción se agregaría en el proxy o con middleware.
- **Sin persistencia**: No hay base de datos. La API es stateless.
- **Sin TLS**: La comunicación es HTTP plano. En producción, TLS se termina en el load balancer o en Nginx.
- **Rate limiting por IP**: En entornos con NAT compartido, múltiples usuarios legítimos podrían compartir IP y verse afectados.

## Riesgos y Mejoras para Producción

### Despliegue y Orquestación

- Migrar de Docker Compose a Kubernetes (EKS/GKE) con manifiestos Helm o Kustomize.
- Gestión declarativa del estado con GitOps (ArgoCD/FluxCD).
- Estrategia blue-green o canary para deploys sin downtime.

### Rollback

- Imágenes tagueadas por commit SHA permiten rollback exacto a cualquier versión.
- En K8s: `kubectl rollout undo` o revert del commit en GitOps.

### Logging

- Estructurar logs en formato JSON para parsing automatizado.
- Centralizar con Promtail/Loki, FluentBit, o CloudWatch Logs.
- Correlación de requests con trace IDs.

### Métricas y Alertas

- Exponer métricas con Prometheus (latencia, error rate, requests/s).
- Dashboards en Grafana para visualización.
- Alertas con Alertmanager: notificar si `/health` falla o si errores 5xx superan umbral (SLOs/SLIs).

### Secrets

- No hardcodear credenciales en código ni en imágenes.
- Usar AWS Secrets Manager, HashiCorp Vault, o GitHub Secrets para inyección en runtime.
- Rotación automática de secrets.

### Escalabilidad

- Horizontal Pod Autoscaler (HPA) basado en CPU/memoria.
- El cálculo de MD5 es CPU-bound: escalar horizontalmente ante picos.
- Load balancer (ALB/NLB) distribuyendo tráfico entre réplicas.

### Seguridad

- Terminación TLS en el load balancer o Ingress Controller (Let's Encrypt/ACM).
- Network policies para aislar pods.
- WAF para protección contra ataques comunes.
- Escaneo de imágenes con Trivy en CI (ya implementado).
- Pod Security Standards (restricted).

### Container Registry

- ECR/GCR como registry privado.
- Semantic versioning + tags inmutables.
- Lifecycle policies para limpieza de imágenes antiguas.

### Límites de Recursos

- Definir requests y limits de CPU/memoria en los manifiestos K8s.
- Evitar escenarios de noisy neighbor y OOMKills.
- Resource quotas por namespace.

## Estructura del Proyecto

```
urbetrack-challenge/
├── app/
│   ├── __init__.py
│   ├── main.py              # API FastAPI (endpoints + lógica MD5)
│   └── requirements.txt     # Dependencias pinneadas
├── nginx/
│   └── nginx.conf           # Reverse proxy + rate limiting
├── scripts/
│   ├── build.sh             # Construir imágenes
│   ├── start.sh             # Levantar stack
│   ├── stop.sh              # Detener stack
│   ├── healthcheck.sh       # Monitoreo de salud (configurable)
│   └── dev.sh               # Desarrollo con hot-reload
├── tests/
│   ├── conftest.py          # Fixtures pytest
│   ├── test_normalize.py    # Property test: key-order independence
│   ├── test_validate_md5.py # Property test: round-trip validation
│   └── requirements-test.txt
├── .github/workflows/
│   └── ci.yml               # Pipeline CI (build, scan, validate, test)
├── Dockerfile               # Multi-stage, non-root, healthcheck
├── docker-compose.yml       # Stack producción (API + Nginx)
├── docker-compose.dev.yml   # Override para desarrollo
├── .dockerignore
├── .gitignore
└── README.md
```

## CI Pipeline

El workflow de GitHub Actions valida automáticamente en cada push:

1. Checkout del código (historial completo)
2. **Secret scanning** con Gitleaks (detecta credenciales expuestas en código e historial)
3. **SAST** con Bandit (análisis estático de seguridad del código Python)
4. Build de imagen Docker (con cache de layers)
5. Tag de imagen con SHA del commit (trazabilidad)
6. Escaneo de vulnerabilidades de imagen con Trivy (HIGH/CRITICAL)
7. Validación de sintaxis Docker Compose
8. Levantamiento del stack completo
9. Healthcheck real contra la API corriendo
10. Test funcional contra `/validate-md5` (hash calculado dinámicamente)
11. Cleanup

Se demuestra inyección de secrets mediante variable de entorno simulada desde GitHub Secrets.

## Tests

```bash
# Instalar dependencias de test
pip install -r app/requirements.txt -r tests/requirements-test.txt

# Ejecutar tests
pytest tests/ -v
```

Los property-based tests (Hypothesis) generan 100 inputs aleatorios por propiedad y verifican que se cumplan siempre:
- **Round-trip**: hash correcto siempre retorna 200
- **Key-order independence**: mismo dato con claves desordenadas produce mismo hash
