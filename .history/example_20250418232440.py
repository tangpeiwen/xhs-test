from fastapi import FastAPI
import uvicorn

app = FastAPI()

# @app.get("/hello")
@app.get("")
def say_hello():
    return {"message": "你好，世界！"}

# if __name__ == "__main__":
#     uvicorn.run("example:app", host="0.0.0.0", port=8000, reload=True) 