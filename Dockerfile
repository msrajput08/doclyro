FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl openssl ghostscript libreoffice-writer libreoffice-calc libreoffice-impress \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-fra tesseract-ocr-deu tesseract-ocr-spa fonts-dejavu-core \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    icc-profiles-free && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY static ./static
# Pin the matching PDF.js library + worker to the Docker image. Browser previews
# stay on our own origin and do not depend on third-party CDN availability.
RUN mkdir -p ./static/vendor && \
    curl -fsSL --retry 3 --connect-timeout 15 https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js -o ./static/vendor/pdf.min.js && \
    curl -fsSL --retry 3 --connect-timeout 15 https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js -o ./static/vendor/pdf.worker.min.js
RUN useradd --system --uid 10001 --create-home --home-dir /home/pdfcraft pdfcraft \
    && mkdir -p /workspace/data && chown -R pdfcraft:pdfcraft /workspace/data
USER pdfcraft
EXPOSE 8000
CMD ["sh","-c","exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
