FROM node:24-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_COLAB_NOTEBOOK_URL
ENV VITE_COLAB_NOTEBOOK_URL=${VITE_COLAB_NOTEBOOK_URL}
RUN npm run build

FROM python:3.12-slim-bookworm
ENV APP_MODE=space \
    HOME=/home/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
RUN groupadd --gid 1000 app && useradd --uid 1000 --gid 1000 --create-home app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=1000:1000 src/ ./src/
COPY --chown=1000:1000 tools/build_index.py ./tools/
COPY --chown=1000:1000 results/*.json ./results/
COPY --chown=1000:1000 artifacts/index.npz artifacts/thumbs.pack artifacts/scale.json ./artifacts/
COPY --chown=1000:1000 app_assets/gallery/ ./app_assets/gallery/
COPY --from=frontend-build --chown=1000:1000 /build/frontend/dist/ ./frontend/dist/
USER 1000:1000
EXPOSE 7860
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
