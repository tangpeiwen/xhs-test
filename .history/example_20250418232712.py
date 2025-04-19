from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")                      # 首页
def read_root():
    return {"message": "这是首页"}

@app.get("/hello")                # 固定路径
def say_hi():
    return {"message": "你好"}

@app.get("/hello/{name}")         # 动态路径
def greet(name: str):
    return {"message": f"你好，{name}"}

if __name__ == "__main__":
    uvicorn.run("example:app", host="0.0.0.0", port=8000, reload=True) 