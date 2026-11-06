"""Start the API + dashboard:  python run.py
Dashboard: http://127.0.0.1:8000/dashboard    Interactive API docs: http://127.0.0.1:8000/docs"""
import uvicorn

from app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
