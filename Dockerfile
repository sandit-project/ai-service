FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 설치 (필요 시)
RUN apt-get update && apt-get install -y build-essential gcc

# 소스 전체 복사
COPY . .

# poetry 설치 및 의존성 설치
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9008", "--reload"]
