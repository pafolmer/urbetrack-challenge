# =============================================================================
# Stage 1: Builder — instala dependencias en directorio aislado
# =============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Copiar solo requirements.txt primero (cache de layers: si no cambian las deps,
# Docker reutiliza esta capa sin re-descargar paquetes)
COPY app/requirements.txt .

# Instalar dependencias en /install para copiarlas limpias al stage final
# --no-cache-dir: no guardar cache de pip (reduce tamaño de la capa)
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# =============================================================================
# Stage 2: Runtime — imagen final liviana, solo lo necesario para ejecutar
# =============================================================================
FROM python:3.12-slim

# Crear usuario non-root (seguridad: si alguien explota la app, no es root)
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copiar dependencias instaladas desde el builder a /usr/local
# (ahí Python busca librerías y /usr/local/bin está en PATH → uvicorn disponible)
COPY --from=builder /install /usr/local

# Copiar código de la aplicación
COPY app/ .

# Cambiar a usuario non-root antes de ejecutar
USER appuser

# Documentar el puerto que usa la app (no lo expone, solo metadata)
EXPOSE 8000

# Healthcheck nativo de Docker: cada 30s verifica que /health responda
# Docker marca el contenedor como "unhealthy" si falla 3 veces seguidas
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Comando por defecto: levantar uvicorn escuchando en todas las interfaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
