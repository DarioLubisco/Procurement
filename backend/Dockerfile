FROM python:3.12-slim

# Evitar prompts durante las instalaciones
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias esenciales y librerías ODBC
RUN apt-get update && apt-get install -y \
    curl \
    gnupg2 \
    unixodbc \
    unixodbc-dev \
    gcc \
    g++ \
    apt-transport-https

# Instalar herramientas necesarias y llaves de Microsoft corregidas (Debian 12 Bookworm)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Configurar directorio de trabajo
WORKDIR /app

# Instalar los paquetes de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo nuestro propio código fuente
COPY . .

# Exponer el puerto de Uvicorn (FastAPI)
EXPOSE 8000

# Lanzar el servidor al encender contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
