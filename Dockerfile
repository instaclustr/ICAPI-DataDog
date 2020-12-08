FROM python:3.9.0-alpine3.12

# Need python3 dependencies
RUN apk add build-base --update
# Generic container setup
WORKDIR /usr/app
RUN addgroup -g 1001 -S appgroup && \
adduser -u 1001 -S appuser -G appgroup && \
chown -R appuser:appgroup /usr/app
USER appuser

# Dependency setup
ADD requirements.txt .
RUN pip install -r requirements.txt --user

# App setup
ENV DD_API_KEY DD_APP_KEY
COPY instaclustr instaclustr
COPY localdatadog localdatadog
ADD ic2datadog.py .

CMD ["python", "ic2datadog.py"]