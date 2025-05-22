FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 설치 (필요한 경우에 따라 조정 가능)
RUN apt-get update && apt-get install -y build-essential gcc

# 소스 복사
COPY . .

# Poetry 설치 및 의존성 설치
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9008"]

