FROM python:3.11-alpine
RUN addgroup -S sandbox && adduser -S sandbox -G sandbox
WORKDIR /sandbox
COPY docker/runner.py /sandbox/runner.py
USER sandbox
ENTRYPOINT ["python", "/sandbox/runner.py"]
