ARG BUILD_FROM
FROM $BUILD_FROM

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Python + venv (install deps into venv to avoid PEP 668 restrictions)
RUN apk add --no-cache python3 py3-pip \
    && python3 -m venv "$VIRTUAL_ENV" \
    && "$VIRTUAL_ENV/bin/pip" install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN "$VIRTUAL_ENV/bin/pip" install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
RUN "$VIRTUAL_ENV/bin/python" -m compileall -q /app/app
COPY www /app/www
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
