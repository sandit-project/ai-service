FROM python:3.10-slim

WORKDIR /app

# poetry 설치
RUN pip install --no-cache-dir poetry

# 소스 전체 복사
COPY . .

# 의존성 설치 (가상환경 안쓰고 시스템에 바로 설치)
RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9008", "--reload"]

