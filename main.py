# ai-service/main.py
import os
import json
from fastapi.responses import JSONResponse
import openai
from fastapi import Body, FastAPI, HTTPException
import database
from schemas import AllergyList, AllergyCheckReq, AllergyCheckRes, SaveAllergyReq

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
    """
    특정 사용자(social_uid)의 알러지 항목 목록을 조회합니다.
    """
    conn = database.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT allergy FROM user_allergy WHERE social_uid = %s ORDER BY created_date",
            (social_uid,)
        )
        rows = cursor.fetchall() or []
        allergy_names = [row["allergy"] for row in rows]
        return AllergyList(allergy=allergy_names)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")
    finally:
        cursor.close()
        conn.close()

# ---- 유저 알러지 저장 ----
@app.post("/api/ai/user-allergy")
async def save_user_allergy(data: SaveAllergyReq = Body(...)):
    """
    회원(일반/소셜)의 알러지 정보 DB에 저장
    """
    if not data.user_uid and not data.social_uid:
        raise HTTPException(status_code=400, detail="user_uid 또는 social_uid가 필요합니다.")
    conn = database.get_connection()
    cursor = conn.cursor()
    
    try:
        for allergy in data.allergies:
            cursor.execute(
                "INSERT INTO user_allergy (user_uid, social_uid, allergy) VALUES (%s, %s, %s) ",
                (data.user_uid, data.social_uid, allergy,)
            )
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"DB 저장 오류: {e}")
    finally:
        cursor.close()
        conn.close()

# --- "알러지 정보 수정" 엔드포인트 추가 (일반/소셜 통합) --- #
@app.put("/api/ai/user-allergy")
async def update_user_allergy(data: SaveAllergyReq = Body(...)):
    """
    회원(일반/소셜) 알러지 정보를 수정(덮어쓰기: 기존 데이터 삭제 후 새로 저장)
    """
    if not data.user_uid and not data.social_uid:
        raise HTTPException(status_code=400, detail="user_uid 또는 social_uid가 필요합니다.")

    conn = database.get_connection()
    cursor = conn.cursor()
    try:
        # 기존 알러지 모두 삭제
        if data.user_uid:
            cursor.execute("DELETE FROM user_allergy WHERE user_uid=%s", (data.user_uid,))
        elif data.social_uid:
            cursor.execute("DELETE FROM user_allergy WHERE social_uid=%s", (data.social_uid,))
        # 새로 입력
        for allergy in data.allergies:
            cursor.execute(
                "INSERT INTO user_allergy (user_uid, social_uid, allergy) VALUES (%s, %s, %s)",
                (data.user_uid, data.social_uid, allergy)
            )
        conn.commit()
        return {"success": True}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"DB 저장 오류: {e}")
    finally:
        cursor.close()
        conn.close()    
        
# ---- 알러지 검사 ----
@app.post("/api/ai/check-allergy", response_model=AllergyCheckRes)
async def check_allergy(req: AllergyCheckReq):
    """
    OpenAI API를 통해 사용자의 알러지와 선택된 재료를 검사하여 위험 여부를 반환합니다.
    """
    print("==== [req 내용 출력] ====")
    print(req)
    print("==== [req 내용 출력] 끝 ====")
    
    
    # 1) DB에서 사용자의 알러지 목록 조회(user_uid 또는 social_uid)
    user_allergies = []
    conn = database.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if req.user_uid is not None:
            cursor.execute("SELECT allergy FROM user_allergy WHERE user_uid = %s", (req.user_uid,))
            user_allergies = [r["allergy"] for r in cursor.fetchall() or []]
        elif req.social_uid is not None:
            cursor.execute("SELECT allergy FROM user_allergy WHERE social_uid = %s", (req.social_uid,))
            user_allergies = [r["allergy"] for r in cursor.fetchall() or []]
            
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
    prompt = f"""
            당신은 엄격한 식품 알러지 검사 어시스턴트입니다.

            [알러지 검사 규칙]
            - 반드시 [선택된 재료] 리스트 중에서만 위험 cause를 추출하세요.
            - 사용자의 알러지와 직접적으로 관련된 재료만 cause에 포함하세요.
            - 사용자의 알러지와 무관하거나, [선택된 재료]에 없는 재료는 절대 cause에 포함하지 마세요.
            - 베이컨, 햄, 치킨, 소고기, 양상추, 토마토, 오이, 피망 등 **고기류, 채소, 소스**는 계란(난류) 알러지와 무관합니다. 그러므로 cause에 포함하지 마세요.
            - **특히, 모짜렐라 치즈, 체다 치즈, 파마산 치즈 등 치즈류는 오직 우유(유제품) 알러지에만 위험 cause입니다. 난류(계란) 알러지에는 절대 cause에 포함하지 마세요.**
            - **만약 cause가 빈 배열([])이면 risk는 반드시 false로 답하세요.**
            - 예시1: 사용자 알러지: ['난류'], 선택된 재료: ['위트', '모짜렐라 치즈', '토마토', '베이컨']
                → cause는 [] (빈 리스트, 위험 없음)
            - 예시2: 사용자 알러지: ['난류'], 선택된 재료: ['스크램블에그', '양상추']
                → cause는 ['스크램블에그']
            - 예시3: 사용자 알러지: ['우유'], 선택된 재료: ['모짜렐라 치즈', '토마토']
                → cause는 ['모짜렐라 치즈']
            - 결과는 반드시 아래 JSON 포맷만 반환하세요:
            {{"risk": bool, "cause": [string], "detail": string}}
            - JSON 외의 설명은 절대 포함하지 마세요.

            [사용자 알러지]
            {user_allergies}

            [선택된 재료]
            {clean_ingredients}
            """



    # 3) OpenAI API 호출
    # 최신 1.x 방식으로 호출
    print("보내는 prompt:", prompt)
    print("ingredients:", clean_ingredients)
    print("user_allergies:", user_allergies)

    try:
    
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
            



