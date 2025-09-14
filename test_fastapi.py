from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "FastAPI is working!"}

@app.get("/test")
def test_endpoint():
    return {"status": "success", "message": "Test endpoint working"}