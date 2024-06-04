# 自訂通知客戶端
  請遵照`src/notification/template.py`的格式，實作：
  - `send_eew`：發送速報消息，主程式呼叫該函式時會傳入速報資料
  - `update_eew`：更新現存的速報資料，主程式呼叫該函式時會傳入欲更新的速報資料
  - `lift_eew`：解除速報（通常會於速報發送後的4分鐘解除，視API資料），主程式呼叫該函式時會傳入欲解除警報的速報資料
  - `run`：啟動客戶端，如果該部分不需執行任何操作，則填寫`pass`即可

    就像這樣：
    ```py
    async def run(self):
      pass
    ```

  注意：請將這些函式宣告為協程(coroutine)，且避免使用阻塞呼叫(blocking calls)
  
  例如：
  ```py
  async def send_eew(self, eew: EEW):
    await aiohttp.request("POST", url, ...)  # use non-blocking calls
  ```
  會優於：
  ```py
  async def send_eew(self, eew: EEW):
    requests.post(url, ...)  # do not use blocking calls
  ```

# 一同貢獻
  **歡迎將你寫的自訂通知客戶端發PR合併至主要分支，讓大家能一起使用更廣泛、多元的功能！**
