# 베이스 이미지
FROM python:3.11-slim

# 작업 디렉토리
WORKDIR /app

# pyproject.toml 복사 & 의존성 설치
COPY pyproject.toml .
RUN pip install --no-cache-dir uvicorn fastapi && pip install --no-cache-dir .

# 전체 소스 복사
COPY . .

# 컨테이너 포트 열기 (FastAPI 기본)
EXPOSE 9008

# FastAPI 실행 명령 (app=main.py 안의 FastAPI 인스턴스)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9008"]
