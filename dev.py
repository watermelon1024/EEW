import asyncio
import random
import threading
import time

from aiohttp import web

from src.client.http import API_NODES
from src.main import main

DEV_SERVER_HOST = "127.0.0.1"
DEV_SERVER_PORT = 8000

app = web.Application()
routes = web.RouteTableDef()


def _main_wrapper():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    API_NODES.clear()
    API_NODES.append(f"{DEV_SERVER_HOST}:{DEV_SERVER_PORT}")
    main()


async def background_task(_):
    thread = threading.Thread(target=_main_wrapper)
    thread.daemon = True
    thread.start()


app.on_startup.append(background_task)
app.on_cleanup.append(lambda _: loop.stop())

content = []
eq_id = 1130699


async def update_earthquake_data():
    global eq_id
    await asyncio.sleep(10)
    eq_id += 1
    earthquake_data = {
        "id": f"{eq_id}",
        "author": "測試資料",
        "serial": 1,
        "final": 0,
        "eq": {
            "lat": 24.23,
            "lon": 122.16,
            "depth": 40,
            "loc": "花蓮縣外海",
            "mag": 6.9,
            "time": int(time.time() - 12.5) * 1000,  # 使用當前時間
            "max": 5,
        },
        "time": int(time.time() * 1000),  # 使用當前時間
    }
    content.append(earthquake_data)
    while True:
        await asyncio.sleep(random.uniform(0.5, 3))
        earthquake_data["serial"] += 1
        earthquake_data["eq"]["mag"] += random.uniform(-0.05, 0.1)  # 模擬震級變化
        earthquake_data["eq"]["mag"] = round(earthquake_data["eq"]["mag"], 1)
        earthquake_data["eq"]["depth"] += random.randint(-1, 3) * 5  # 模擬深度變化
        earthquake_data["eq"]["lat"] += random.uniform(-0.2, 0.1)  # 模擬經緯度變化
        earthquake_data["eq"]["lon"] += random.uniform(-0.2, 0.1)
        earthquake_data["eq"]["lat"] = round(earthquake_data["eq"]["lat"], 2)
        earthquake_data["eq"]["lon"] = round(earthquake_data["eq"]["lon"], 2)
        current_time = int(time.time() * 1000)
        earthquake_data["time"] = current_time  # 更新發報時間
        if earthquake_data["serial"] >= 5:
            earthquake_data["final"] = 1  # 假設 5 次更新後即為最終報告
            break
    await asyncio.sleep(20)
    content.pop(0)


@routes.get("/api/v1/eq/eew")
async def get_earthquake(request):
    return web.json_response(content)


@routes.get("/post")
async def post_earthquake(request):
    asyncio.create_task(update_earthquake_data())
    return web.Response(text="Started earthquake data update task")


app.add_routes(routes)

if __name__ == "__main__":
    web.run_app(app, host=DEV_SERVER_HOST, port=DEV_SERVER_PORT)
