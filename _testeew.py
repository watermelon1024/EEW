import random
import threading
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

content = []
eq_id = 1130699


def update_earthquake_data():
    time.sleep(15)
    global eq_id
    eq_id += 1
    earthquake_data = {
        "id": f"{eq_id}",
        "author": "測試資料",
        "serial": 1,
        "final": 0,
        "eq": {
            "lat": 24.03,
            "lon": 122.16,
            "depth": 40,
            "loc": "花蓮縣外海",
            "mag": 6.2,
            "time": int((time.time() - 15) * 1000),
            "max": 4,
        },
        "time": int(time.time() * 1000),  # 使用當前時間
    }
    content.append(earthquake_data)
    while True:
        time.sleep(random.uniform(2, 3))
        earthquake_data["serial"] += 1
        earthquake_data["eq"]["mag"] += random.uniform(-0.05, 0.1)  # 模擬震級變化
        earthquake_data["eq"]["mag"] = round(earthquake_data["eq"]["mag"], 1)
        earthquake_data["eq"]["depth"] += random.randint(-1, 3) * 10  # 模擬深度變化
        earthquake_data["eq"]["lat"] += random.uniform(-0.2, 0.1)  # 模擬經緯度變化
        earthquake_data["eq"]["lon"] += random.uniform(-0.2, 0.1)
        earthquake_data["eq"]["lat"] = round(earthquake_data["eq"]["lat"], 2)
        earthquake_data["eq"]["lon"] = round(earthquake_data["eq"]["lon"], 2)
        earthquake_data["eq"]["depth"] = max(10, earthquake_data["eq"]["depth"])
        current_time = int(time.time() * 1000)
        earthquake_data["time"] = current_time  # 更新發報時間
        if earthquake_data["serial"] >= 3:
            earthquake_data["final"] = 1  # 假設 3 次更新後即為最終報告
            break
    time.sleep(30)
    content.pop(0)


@app.get("/api/v1/eq/eew")
async def get_earthquake():
    return JSONResponse(content=content)


@app.get("/post")
async def post_earthquake():
    update_thread = threading.Thread(target=update_earthquake_data)
    update_thread.daemon = True
    update_thread.start()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)