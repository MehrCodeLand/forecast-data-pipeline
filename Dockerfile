FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    cron \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/logs

RUN echo "0 * * * * cd /app && /usr/local/bin/python /app/fetch_weather.py >> /app/logs/cron.log 2>&1" > /etc/cron.d/weather-cron
RUN chmod 0644 /etc/cron.d/weather-cron
RUN crontab /etc/cron.d/weather-cron
RUN touch /var/log/cron.log

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]