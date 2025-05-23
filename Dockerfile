FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 설치 (필요 시 조정)
RUN apt-get update && apt-get install -y build-essential gcc && apt-get clean && rm -rf /var/lib/apt/lists/*

# 소스 코드 복사
COPY . .

# Poetry 설치 및 의존성 설치
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# openai 라이브러리 최신 버전 설치 (poetry에 없으면 직접 설치)
RUN pip install --no-cache-dir --upgrade openai

# 컨테이너 실행 커맨드
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9008"]
