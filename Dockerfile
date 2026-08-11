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

# Aplica migraciones y arranca el servidor
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
