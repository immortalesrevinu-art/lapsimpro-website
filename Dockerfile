FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LAPSIMPRO_HOST=0.0.0.0 \
    PORT=8787 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 user

WORKDIR /home/user/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .
RUN mkdir -p /home/user/app/data && chown user:user /home/user/app/data

USER user
EXPOSE 8787

CMD ["python", "-m", "server"]
