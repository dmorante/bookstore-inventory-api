# Imagen base ligera y moderna
FROM python:3.12-slim

# Evita que Python guarde .pyc y activa logs sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instala dependencias primero para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copia el código de la aplicación
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000

# Aplica migraciones y arranca el servidor.
#
# El puerto se toma de $PORT si existe (los PaaS como Render, Railway o
# Cloud Run lo inyectan y esperan que la app escuche ahí) y cae a 8000
# en local, donde docker-compose no define esa variable.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
