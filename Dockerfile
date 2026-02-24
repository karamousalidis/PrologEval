FROM python:3.13-slim

# Install SWI-Prolog (provides libswipl for PySwip)
RUN apt-get update && \
    apt-get install -y --no-install-recommends swi-prolog && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project metadata first for layer caching
COPY pyproject.toml ./

# Install Python dependencies from pyproject.toml
RUN pip install --no-cache-dir .

# Copy source code
COPY . .

# Ensure temp directory exists for generated Prolog files
RUN mkdir -p temp

EXPOSE 8501

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
