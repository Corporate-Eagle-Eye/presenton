FROM python:3.11-slim-bookworm

# Install essential packages with proper cleanup
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    wget \
    ca-certificates \
    gnupg \
    build-essential \
    libreoffice \
    fontconfig \
    chromium \
    && rm -rf /var/lib/apt/lists/*


# Install Node.js 20 using NodeSource repository
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*


# Create a working directory
WORKDIR /app  

# Set environment variables
ENV APP_DATA_DIRECTORY=/app_data
ENV TEMP_DIRECTORY=/tmp/presenton
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium


# Install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install dependencies for FastAPI with proper error handling
RUN pip install --no-cache-dir aiohttp aiomysql aiosqlite asyncpg fastapi[standard] \
    pathvalidate pdfplumber sqlmodel httpx \
    anthropic google-genai openai fastmcp dirtyjson \
    python-pptx lxml pillow && \
    pip install --no-cache-dir chromadb || echo "ChromaDB installation failed, continuing..." && \
    pip install --no-cache-dir docling --extra-index-url https://download.pytorch.org/whl/cpu || echo "Docling installation failed, continuing..."

# Install dependencies for Next.js
WORKDIR /app/servers/nextjs
COPY servers/nextjs/package.json servers/nextjs/package-lock.json ./
RUN npm install

# Install Sharp for ARM64 image optimization (if needed)
RUN npm install sharp

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

# Expose the correct port
EXPOSE 9000

# Start the servers
CMD ["node", "/app/start.js"]