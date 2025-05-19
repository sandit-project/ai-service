# ai-service/main.py
import os
import json
import openai
from fastapi import FastAPI, HTTPException
import database
from schemas import AllergyList, AllergyCheckReq, AllergyCheckRes
from database import get_connection

# 환경변수 로드 (이미 database.py에서 dotenv 로드하므로 중복 불필요)
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. .env를 확인하세요.")

app = FastAPI(title="AI Service")

@app.get("/api/ai/users/{user_uid}/allergies", response_model=AllergyList)
async def get_user_allergies(user_uid: int):
    """
    특정 사용자(user_uid)의 알러지 항목 목록을 조회합니다.
    """
    conn = database.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT allergy FROM user_allergy WHERE user_uid = %s ORDER BY created_date",
            (user_uid,)
        )
        rows = cursor.fetchall() or []
        allergy_names = [row["allergy"] for row in rows]
        return AllergyList(allergy=allergy_names)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/ai/check-allergy", response_model=AllergyCheckRes)
async def check_allergy(req: AllergyCheckReq):
    """
    OpenAI API를 통해 사용자의 알러지와 선택된 재료를 검사하여 위험 여부를 반환합니다.
    """
    # 1) DB에서 사용자의 알러지 목록 조회
    conn = database.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT allergy FROM user_allergy WHERE user_uid = %s",
            (req.user_id,)
        )
        rows = cursor.fetchall() or []
        user_allergies = [r["allergy"] for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")
    finally:
        cursor.close()
        conn.close()

    # 2) OpenAI 프롬프트 작성
    prompt = (
        f"당신은 알러지 검사 어시스턴트입니다."
        f"사용자 알러지 목록: {', '.join(user_allergies) or '없음'}. "
        f"선택된 재료: {', '.join(req.ingredients)}. "
        "위험한 재료가 있는지 검토하고, JSON 형식으로만 응답해주세요.\n"
        "{\n"
        "  \"risk\": boolean,  # 위험 여부\n"
        "  \"cause\": [string],  # 위험 재료 리스트\n"
        "  \"detail\": string  # 설명\n"
        "}\n"
    )
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "알러지 검사 어시스턴트"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        return AllergyCheckRes(**data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"AI 응답 파싱 실패: {content}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 호출 실패: {e}")
        



