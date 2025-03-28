# Use an official Python runtime
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies BEFORE switching users (important)
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user
RUN useradd -m appuser
RUN chown -R appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV HF_HOME=/app/.cache/huggingface
ENV TORCH_HOME=/app/.cache/torch
ENV PATH="/home/appuser/.local/bin:$PATH"  

# Expose API port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]



