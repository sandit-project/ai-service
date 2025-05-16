# FastAPI를 사용하여 알러지 체크 API 서버 구현
from fastapi import FastAPI, APIRouter,HTTPException
from pydantic import BaseModel
import openai
import os
import pymysql
import json
import uvicorn
from dotenv import load_dotenv

if __name__ == "__main__":
    uvicorn.run(
        "ai_service:app",
        host=os.getenv("AI_SERVICE_HOST", "0.0.0.0"),#외부접근허용
        port=int(os.getenv("AI_SERVICE_PORT", 9008)),# .env에 추가 가능
        reload=True, # 개발 중 자동 재시작
    )

# 환경 변수 로드
load_dotenv()

# 환경변수로부터 DB 설정 읽기
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
AI_DB   = os.getenv("AI_DB_NAME", "ai")
AUTH_DB = os.getenv("AUTH_DB_NAME", "auth")  # auth 스키마는 이미 존재

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# FastAPI 앱 초기화
app = FastAPI()

# 데이터베이스 및 테이블 초기화
# 서버 시작 시 AI DB 및 user_allergy 테이블 생성
def init_db():
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
    try:
        with conn.cursor() as cursor:
            # AI DB 생성 (없는 경우)
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{AI_DB}`;")
            # AI DB로 전환 후 테이블 생성
            cursor.execute(f"USE `{AI_DB}`;")
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS `{AI_DB}`.`user_allergy` (
                    uid BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_uid BIGINT NOT NULL,
                    allergy VARCHAR(255) NOT NULL,
                    created_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_uid) REFERENCES `{AUTH_DB}`.`user`(uid)
                ) ENGINE=InnoDB;
                """
            )
    finally:
        conn.close()

# 앱 시작 시 DB 초기화
init_db()

# 요청 모델 정의
class AllergyCheckRequest(BaseModel):
    user_id: str
    ingredients: list[str]

# 응답 모델 정의
class AllergyCheckResponse(BaseModel):
    risk: bool
    cause: list[str] | None
    detail: str

# 사용자 알러지 조회 함수
def get_user_allergies(user_id: str) -> list[str]:
    conn = pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        db=AI_DB,
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with conn.cursor() as cursor:
            sql = (
                f"SELECT ua.allergy "
                f"FROM `{AI_DB}`.`user_allergy` ua "
                f"JOIN `{AUTH_DB}`.`user` u ON ua.user_uid = u.uid "
                f"WHERE u.user_id = %s"
            )
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()
            return [row['allergy'] for row in rows]
    finally:
        conn.close()

# "/api/ai"를 기본 경로로 갖는 라우터 생성
router = APIRouter(prefix="/api/ai")

# 알러지 체크 엔드포인트
@router.post("/check-allergy", response_model=AllergyCheckResponse)
async def check_allergy(req: AllergyCheckRequest):
    try:
        # DB에서 유저 알러지 조회
        user_allergies = get_user_allergies(req.user_id)
        if not user_allergies:
            return AllergyCheckResponse(
                risk=False,
                cause=[],
                detail="등록된 알러지가 없습니다."
            )

        # OpenAI 프롬프트 구성
        prompt = (
            f"유저 알러지: {', '.join(user_allergies)}\n"
            f"주문 재료: {', '.join(req.ingredients)}\n"
            "위험 여부와 원인을 JSON {\"risk\":bool, \"cause\":[\"...\"], \"detail\":\"...\"} 형식으로만 응답해줘."
        )

        # OpenAI 호출
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 식품 알러지 전문 의사야."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200
        )
        # JSON 파싱
        data = json.loads(response.choices[0].message.content)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# FastAPI 앱에 라우터 등록
app.include_router(router)
