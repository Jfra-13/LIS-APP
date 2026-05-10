FROM python:3.12-slim

# Evita que Python genere archivos temporales .pyc
ENV PYTHONDONTWRITEBYTECODE 1
# Asegura que los logs salgan en la terminal en tiempo real
ENV PYTHONUNBUFFERED 1

WORKDIR /code

# Instalamos dependencias del sistema operativo necesarias para Postgres y compilaciones
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos e instalamos dependencias de Python
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m spacy download es_core_news_sm

# Descargamos el modelo base de Machine Learning (NLP) para español
RUN python -m spacy download es_core_news_md

# Copiamos el resto del proyecto
COPY . /code/