FROM python:3.11-slim

# Install system packages first
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    gnupg \
    nginx \
    libreoffice \
    fontconfig \
    chromium \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 using NodeSource repository
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install newer SQLite version (3.44.0) to meet ChromaDB requirements
RUN cd /tmp && \
    wget https://www.sqlite.org/2023/sqlite-autoconf-3440000.tar.gz && \
    tar -xzf sqlite-autoconf-3440000.tar.gz && \
    cd sqlite-autoconf-3440000 && \
    ./configure --prefix=/usr/local && \
    make && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /tmp/sqlite-autoconf-3440000*

# Update environment for the new SQLite
ENV LD_LIBRARY_PATH="/usr/local/lib"

# Create a working directory
WORKDIR /app  

# Set environment variables
ENV APP_DATA_DIRECTORY=/app_data
ENV TEMP_DIRECTORY=/tmp/presenton
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install dependencies for FastAPI - try alternative SQLite approach first
RUN pip install pysqlite3-binary

# Install other dependencies
RUN pip install aiohttp aiomysql aiosqlite asyncpg fastapi[standard] \
    pathvalidate pdfplumber sqlmodel \
    anthropic google-genai openai fastmcp dirtyjson

# Try to install ChromaDB with the updated SQLite
RUN pip install chromadb || echo "ChromaDB installation failed, will use fallback"

RUN pip install docling --extra-index-url https://download.pytorch.org/whl/cpu

# Install dependencies for Next.js
WORKDIR /app/servers/nextjs
COPY servers/nextjs/package.json servers/nextjs/package-lock.json ./
RUN npm install


# Copy Next.js app
COPY servers/nextjs/ /app/servers/nextjs/

# Build the Next.js app
WORKDIR /app/servers/nextjs
RUN npm run build

WORKDIR /app

# Copy FastAPI
COPY servers/fastapi/ ./servers/fastapi/
COPY start.js LICENSE NOTICE ./

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create data directories
RUN mkdir -p /app_data/{images,exports,uploads,fonts}

# Expose the correct port
EXPOSE 9000

# Start the application
CMD ["node", "start.js"]