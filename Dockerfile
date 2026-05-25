FROM python:3.11-slim

WORKDIR /app

# Set Python to unbuffered mode so logs appear immediately
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run with error handling
CMD ["python", "-u", "main_simple.py"]
