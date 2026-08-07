FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-app.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-app.txt

COPY . .

# Railway/Render/Fly all inject PORT; default to 8000 for local docker run.
ENV PORT=8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
