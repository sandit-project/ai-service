# ai-service/database.py
import os
from dotenv import load_dotenv
from mysql.connector import pooling

load_dotenv()  # .env 읽어오기

dbconfig = {
    "host":     os.getenv("SPRING_DATASOURCE_URL") or os.getenv("DB_HOST"),
    "port":     os.getenv("SPRING_DATASOURCE_PORT") or os.getenv("DB_PORT"),
    "user":     os.getenv("SPRING_DATASOURCE_USER") or os.getenv("DB_USER"),
    "password": os.getenv("SPRING_DATASOURCE_PASSWORD") or os.getenv("DB_PASS"),
    "database": os.getenv("DB_NAME", "allergy"),
    "charset":  os.getenv("DB_CHARSET", "utf8mb4"),
    "autocommit": True,
}
# 커넥션 풀 생성
pool = pooling.MySQLConnectionPool(
    pool_name    = "ai_pool",
    pool_size    = 5,
    **dbconfig
)

def get_connection():
    return pool.get_connection()
