# Requirements Document

## Introduction

Challenge técnico para la posición DevOps/SRE en Urbetrack. El sistema consiste en una API REST que valida checksums MD5 de payloads JSON, containerizada con Docker, con Nginx como reverse proxy, automatizada con scripts Bash, y validada mediante un pipeline de GitHub Actions. La entrega prioriza excelencia operacional: documentación, postura de seguridad y preparación para producción.

## Glossary

- **API**: Servicio REST basado en FastAPI (Python 3.12) que expone los endpoints `/validate-md5` y `/health`.
- **Reverse_Proxy**: Contenedor Nginx que rutea tráfico externo desde el puerto 80 hacia la API en la red interna Docker.
- **Compose_Stack**: Entorno Docker Compose compuesto por los servicios API y Reverse_Proxy conectados mediante una red interna.
- **CI_Pipeline**: Workflow de GitHub Actions que construye, valida y testea el Compose_Stack en cada push.
- **JSON_Normalizado**: Representación canónica de un objeto JSON producida al ordenar claves alfabéticamente y usar separadores compactos (`(',', ':')`) sin espacios, codificada en UTF-8.
- **Build_Scripts**: Conjunto de scripts Bash (`build.sh`, `start.sh`, `stop.sh`, `healthcheck.sh`) que automatizan operaciones Docker.
- **Trivy_Scanner**: Scanner de vulnerabilidades de contenedores integrado en el CI_Pipeline.

## Requirements

### Requirement 1: Endpoint POST /validate-md5

> **Cubre:** "POST /validate-md5 — recibir JSON y MD5, validar que el hash corresponda al contenido, responder 200 OK con MD5 si correcto, error HTTP si no coincide"

**User Story:** Como consumidor de la API, quiero enviar un payload JSON con su hash MD5 esperado, para que la API valide la integridad de los datos.

#### Acceptance Criteria

1. WHEN se recibe un POST en `/validate-md5` con un body JSON que contiene un campo `data` y un campo `md5`, THE API SHALL normalizar el campo `data` a JSON_Normalizado, calcular el MD5 del string UTF-8 resultante, y compararlo con el valor `md5` provisto.
2. WHEN el MD5 calculado coincide con el campo `md5` provisto, THE API SHALL retornar HTTP 200 con un body JSON conteniendo el hash MD5 validado.
3. WHEN el MD5 calculado no coincide con el campo `md5` provisto, THE API SHALL retornar un error HTTP adecuado con un body JSON conteniendo un mensaje de error indicando el mismatch.
4. IF el body del request no contiene el campo `data` o el campo `md5`, THEN THE API SHALL retornar HTTP 422 con un error de validación descriptivo.
5. IF el body del request no es JSON válido, THEN THE API SHALL retornar HTTP 422 con un error de parsing descriptivo.

### Requirement 2: Endpoint GET /health

> **Cubre:** "GET /health — responder 200 OK para validar disponibilidad del servicio"

**User Story:** Como ingeniero de operaciones, quiero un endpoint de health, para validar la disponibilidad de la API programáticamente.

#### Acceptance Criteria

1. WHEN se recibe un GET en `/health`, THE API SHALL retornar HTTP 200 con un body JSON indicando estado saludable.
2. THE API SHALL responder a requests de health check sin requerir autenticación ni headers adicionales.

### Requirement 3: Documentación OpenAPI/Swagger

> **Cubre:** "API REST documentada con Swagger/OpenAPI"

**User Story:** Como consumidor de la API, quiero documentación Swagger auto-generada, para explorar y testear la API interactivamente.

#### Acceptance Criteria

1. THE API SHALL exponer una especificación OpenAPI 3.x en el endpoint `/docs` mediante Swagger UI.
2. THE API SHALL exponer el schema OpenAPI en formato JSON en el endpoint `/openapi.json`.
3. THE API SHALL incluir schemas de request/response, ejemplos y códigos de estado en la documentación generada.

### Requirement 4: Dockerfile Optimizado

> **Cubre:** "Dockerfile" + buenas prácticas valoradas (multi-stage, non-root, capas optimizadas)

**User Story:** Como ingeniero DevOps, quiero una imagen de contenedor optimizada, para minimizar la superficie de ataque y reducir tiempos de build.

#### Acceptance Criteria

1. THE API SHALL empaquetarse en una imagen Docker usando una estrategia multi-stage o basada en imagen slim.
2. THE API SHALL ejecutarse como usuario non-root dentro del contenedor.
3. THE API SHALL definir una instrucción HEALTHCHECK nativa de Docker que valide el endpoint `/health`.
4. THE API SHALL ordenar las capas del Dockerfile para maximizar reutilización de cache (dependencias instaladas antes del código de aplicación).

### Requirement 5: Docker Compose Stack

> **Cubre:** "Docker Compose (API + Nginx reverse proxy)"

**User Story:** Como ingeniero DevOps, quiero un solo comando para levantar el entorno completo, para que el sistema sea reproducible y portable.

#### Acceptance Criteria

1. THE Compose_Stack SHALL definir la API y el Reverse_Proxy como servicios separados conectados mediante una red interna Docker.
2. THE Compose_Stack SHALL exponer únicamente el puerto 80 en el host a través del servicio Reverse_Proxy.
3. THE Compose_Stack SHALL NOT exponer el puerto del contenedor API directamente a la red del host.
4. WHEN se ejecuta `docker compose up`, THE Compose_Stack SHALL iniciar ambos servicios y establecer conectividad entre Reverse_Proxy y API dentro de 30 segundos.

### Requirement 6: Configuración Nginx Reverse Proxy

> **Cubre:** "Configuración de Nginx" como reverse proxy

**User Story:** Como ingeniero DevOps, quiero que Nginx esté delante de la API, para que la aplicación esté aislada del acceso externo directo.

#### Acceptance Criteria

1. THE Reverse_Proxy SHALL escuchar en el puerto 80 y reenviar todos los requests HTTP entrantes al contenedor API en la red interna Docker.
2. THE Reverse_Proxy SHALL usar el nombre de servicio Docker para resolución upstream hacia la API.
3. THE Reverse_Proxy SHALL pasar headers de proxy estándar (`X-Forwarded-For`, `X-Real-IP`, `Host`) a la API.
4. THE Reverse_Proxy SHALL implement rate limiting on the /validate-md5 endpoint to mitigate CPU exhaustion from hash computation abuse, allowing burst traffic while rejecting sustained high-frequency requests.

### Requirement 7: Scripts Bash de Automatización

> **Cubre:** "Scripts Bash para: build, start, stop, healthcheck cada 5 segundos" + opcional dev.sh

**User Story:** Como ingeniero DevOps, quiero scripts estandarizados, para que las operaciones Docker sean repetibles y documentadas.

#### Acceptance Criteria

1. WHEN se ejecuta `build.sh`, THE Build_Scripts SHALL construir todas las imágenes Docker definidas en el Compose_Stack.
2. WHEN se ejecuta `start.sh`, THE Build_Scripts SHALL iniciar el Compose_Stack en modo detached.
3. WHEN se ejecuta `stop.sh`, THE Build_Scripts SHALL detener y eliminar todos los contenedores del Compose_Stack.
4. WHEN se ejecuta `healthcheck.sh`, THE Build_Scripts SHALL consultar el endpoint `/health` a través del Reverse_Proxy cada 5 segundos y reportar el estado a stdout.
5. THE Build_Scripts SHALL salir con código no-cero cuando una operación falla.
6. THE Build_Scripts SHALL incluir línea shebang y ser ejecutables (`chmod +x`).
7. WHERE se provee el script opcional `dev.sh`, THE Build_Scripts SHALL iniciar el Compose_Stack con hot-reload habilitado, reconstruyendo y reiniciando el contenedor API automáticamente ante cambios en el código fuente.

### Requirement 8: Pipeline CI con GitHub Actions

> **Cubre:** "Workflow de GitHub Actions" con los pasos mínimos + extras valorados (cache, tags, escaneo)

**User Story:** Como ingeniero DevOps, quiero validación CI automatizada, para que cada push sea verificado en build y salud del runtime.

#### Acceptance Criteria

1. WHEN se hace push al repositorio, THE CI_Pipeline SHALL hacer checkout del código, construir imágenes Docker, validar la configuración del Compose_Stack, levantar el entorno, y ejecutar un healthcheck real contra la API corriendo.
2. THE CI_Pipeline SHALL integrar el Trivy_Scanner para escanear imágenes construidas buscando vulnerabilidades HIGH y CRITICAL.
3. THE CI_Pipeline SHALL usar Docker layer caching para reducir tiempos de build en ejecuciones subsiguientes.
4. THE CI_Pipeline SHALL tagear imágenes construidas con el SHA del commit para trazabilidad.
5. IF algún paso del pipeline falla, THEN THE CI_Pipeline SHALL reportar la falla y detener la ejecución.
6. THE CI_Pipeline SHALL demonstrate secrets injection by passing a simulated environment variable from GitHub Secrets into the container runtime, proving the capability without requiring real credentials.

### Requirement 9: Documentación README

> **Cubre:** "README debe permitir levantar y probar sin asistencia" + "Riesgos y producción"

**User Story:** Como evaluador del challenge, quiero documentación autosuficiente, para entender, ejecutar y evaluar el proyecto sin asistencia externa.

#### Acceptance Criteria

1. THE API SHALL incluir un archivo README conteniendo: pasos para levantar y detener el entorno, ejemplos de requests válidos e inválidos con comandos curl, decisiones técnicas con justificación, explicación del cálculo MD5 con detalles de normalización, supuestos, y limitaciones.
2. THE API SHALL incluir una sección en el README documentando mejoras para producción cubriendo: estrategia de despliegue, procedimientos de rollback, logging, métricas, alertas, gestión de secrets, escalabilidad, hardening de seguridad, container registry, versionado de imágenes, y límites de recursos.

### Requirement 10: Propiedad Round-Trip de Normalización MD5

> **Cubre:** "Explicar cómo calculaste el MD5" — garantiza que la normalización es determinista y verificable

**User Story:** Como desarrollador, quiero verificar que la normalización JSON es determinista, para que los mismos datos lógicos siempre produzcan el mismo hash MD5.

#### Acceptance Criteria

1. FOR ALL objetos JSON válidos, THE API SHALL producir output JSON_Normalizado idéntico independientemente del orden original de claves en el input.
2. FOR ALL objetos JSON válidos, normalizar los datos y calcular MD5, luego re-normalizar los mismos datos y calcular MD5 nuevamente, SHALL producir el mismo hash (propiedad de idempotencia).
3. WHEN el campo `data` contiene objetos anidados, THE API SHALL ordenar claves recursivamente en todos los niveles de anidamiento durante la normalización.
