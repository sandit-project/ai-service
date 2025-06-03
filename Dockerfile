FROM python:3.10-slim

WORKDIR /app

# 시스템 패키지 설치 (gRPC 코드 생성에 gcc 필요)
RUN apt-get update && apt-get install -y build-essential gcc && apt-get clean && rm -rf /var/lib/apt/lists/*

# 소스 복사
COPY . .

# Poetry 설치 및 의존성 설치
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi

# gRPC 관련 패키지 설치 (pyproject.toml에 없어도 대비)
RUN poetry add grpcio grpcio-tools

# .proto 컴파일 (선택 사항)
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. allergy.proto

# 컨테이너 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9008"]
