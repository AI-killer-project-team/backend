Backend Run Guide
# 가상환경 생성 및 활성화

Windows (PowerShell)

python -m venv .venv
. .\.venv\Scripts\Activate.ps1


macOS / Linux

python3 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정

프로젝트 루트에 .env 파일을 생성합니다.

OPENAI_API_KEY=your_key_here

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000


서버 주소: http://localhost:8000



# 헬스 체크

서버가 정상적으로 실행되었는지 확인합니다.

GET http://localhost:8000/health


정상 응답 예시:

{
  "status": "ok"
}