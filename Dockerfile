FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required for pgvector and building Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*