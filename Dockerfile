FROM python:3.11-slim

# Install essential packages only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    gnupg \
    build-essential \
    nginx \
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

# Install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Install Python dependencies with simplified SQLite handling
RUN pip install pysqlite3-binary

# Install core dependencies
RUN pip install aiohttp aiomysql aiosqlite asyncpg fastapi[standard] \
    pathvalidate pdfplumber sqlmodel \
    anthropic google-genai openai fastmcp dirtyjson

# Install ChromaDB with fallback
RUN pip install chromadb || echo "ChromaDB installation skipped"

# Install docling
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