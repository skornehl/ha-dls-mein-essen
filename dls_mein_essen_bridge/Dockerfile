ARG BUILD_FROM
FROM $BUILD_FROM

# The base image (mcr.microsoft.com/playwright/python) ships Chromium and
# all its native dependencies pre-installed at /ms-playwright, but NOT the
# `playwright` pip package itself into whatever venv `python3` resolves to
# here - it still has to be installed explicitly (pinned to match the
# image's tag/browser version, see app/requirements.txt), otherwise
# `import playwright` fails with ModuleNotFoundError at container start.
WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD ["python3", "main.py"]
