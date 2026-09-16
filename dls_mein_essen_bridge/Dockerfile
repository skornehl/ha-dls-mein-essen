ARG BUILD_FROM
FROM $BUILD_FROM

# The base image (mcr.microsoft.com/playwright/python) already ships
# Chromium + all its native dependencies and a matching `playwright` pip
# package - deliberately NOT reinstalling/pinning playwright here to avoid
# a version mismatch against the browser binaries already baked into the
# image at /ms-playwright.
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD ["python3", "main.py"]
