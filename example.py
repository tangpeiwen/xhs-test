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
    # host="0.0.0.0" 允许局域网内的设备访问这个API
    # 在同一网络的iPhone快捷指令中，可以通过 http://[你电脑的局域网IP]:8000/ 访问
    uvicorn.run("example:app", host="0.0.0.0", port=8000, reload=True) 