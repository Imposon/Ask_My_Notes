# Dockerfile for Vortex Finance (FastAPI + Streamlit in one container)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# Using --fix-missing and removing software-properties-common which is often not needed in slim
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY finance_anomaly_backend/requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir streamlit uvicorn

# Copy the rest of the application
COPY finance_anomaly_backend/ /app/

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000
EXPOSE 8501

# Ensure Streamlit is in PATH (common issue in slim images)
ENV PATH="/home/root/.local/bin:${PATH}"

# Create a start script to run both processes
# Use Render's dynamic $PORT for Streamlit (the public-facing UI)
RUN echo '#!/bin/bash\n\
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &\n\
python -m streamlit run streamlit_app.py --server.port ${PORT:-8501} --server.address 0.0.0.0\n\
' > /app/start.sh && chmod +x /app/start.sh

CMD ["/app/start.sh"]
