# ai-service/main.py
import os
import json
from fastapi.responses import JSONResponse
import openai
from fastapi import FastAPI, HTTPException
import database
from schemas import AllergyList, AllergyCheckReq, AllergyCheckRes

print("==== [디버깅용 모델] ====")
print(AllergyCheckReq.model_fields)

# 환경변수 로드 (이미 database.py에서 dotenv 로드하므로 중복 불필요)
# 최신 openai 1.x 방식
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
if not client.api_key:
    raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다. .env를 확인하세요.")

# FastAPI 앱 생성
app = FastAPI(title="AI Service")

# ---- 유저 알러지 조회 ----
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

# ---- 소셜 유저 알러지 조회 ----
@app.get("/api/ai/socials/{social_uid}/allergies", response_model=AllergyList)
async def get_social_allergies(social_uid: int):
    # 예시: social_uid 기반 테이블이 있다면 여기에 구현
    # 기본 샘플: socials 유저는 일단 알러지 정보 없다고 응답
    return AllergyList(allergy=[])

# ---- 알러지 검사 ----
@app.post("/api/ai/check-allergy", response_model=AllergyCheckRes)
async def check_allergy(req: AllergyCheckReq):
    """
    OpenAI API를 통해 사용자의 알러지와 선택된 재료를 검사하여 위험 여부를 반환합니다.
    """
    print("==== [req 내용 출력] ====")
    print(req)
    
    
    # 1) DB에서 사용자의 알러지 목록 조회(user_uid 또는 social_uid)
    user_allergies = []
    conn = database.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if req.user_uid is not None:
            cursor.execute("SELECT allergy FROM user_allergy WHERE user_uid = %s", (req.user_uid,))
            user_allergies = [r["allergy"] for r in cursor.fetchall() or []]
        elif req.social_uid is not None:
            # social_uid 별도 테이블이 있다면 여기에 구현
            # 기본 샘플: socials 유저는 프론트에서 받은 allergy 사용
            user_allergies = req.allergy or []
        else:
            raise HTTPException(status_code=400, detail="user_uid 또는 social_uid가 필요합니다.")
    finally:
        cursor.close()
        conn.close()
     # ★★★★★ ingredients 클린징 추가
    clean_ingredients = [i.strip() for i in req.ingredients if i and i.strip()]
    if not clean_ingredients:
        raise HTTPException(status_code=400, detail="선택된 재료가 없습니다.")

    # 2) OpenAI 프롬프트 작성
    prompt = (
        f"당신은 알러지 검사 어시스턴트입니다."
        f"사용자 알러지 목록: {', '.join(user_allergies) or '없음'}. "
        f"선택된 재료: {', '.join(clean_ingredients)}. "
        "위험한 재료가 있으면 risk:true, cause에는 위험 재료, detail은 한글설명. "
        "JSON만 반환: {\"risk\": bool, \"cause\": [string], \"detail\": string}"
    )
    print("보내는 prompt:", prompt)
    print("ingredients:", clean_ingredients)
    print("user_allergies:", user_allergies)


    try:
        # openai 최신 1.x 방식으로 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            store=True, 
            messages=[
                {"role": "system", "content": "알러지 검사 어시스턴트"},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        # JSON만 추출 보완
        import re
        m = re.search(r'({.*})', content, re.DOTALL)
        if m:
            data = json.loads(m.group(1))
        else:
            raise HTTPException(status_code=500, detail=f"AI 응답에 JSON 없음: {content}")
        response_json = {
            "risk": data.get("risk", False),
            "cause": data.get("cause", []),
            "detail": data.get("detail", "")
        }
        print("AI 응답:", response_json)
        return JSONResponse(content=response_json, media_type="application/json")
    
        
        
    except Exception as e:
        import traceback
        print("========== [AI API 호출 예외 발생] ==========")
        print("보낸 프롬프트:", prompt)
        print("에러 타입:", type(e))
        print("에러 메시지:", e)
        traceback.print_exc()
        print("=============================================")
        raise HTTPException(status_code=500, detail=f"AI 호출 실패: {e}")
            



