FROM python:3.12-slim

WORKDIR /e2e

COPY e2e/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY e2e/ .
COPY evil-repos/ /evil-repos/

CMD ["pytest", "-v", "--tb=short", "test_e2e.py"]
