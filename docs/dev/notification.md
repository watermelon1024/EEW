# 自訂通知客戶端
  請遵照`src/notification/template.py`的格式，實作：
  - `send_eew`：發送速報消息，主程式收到新速報時，會呼叫該函式並傳入速報資料
    ```py
    async def send_eew(self, eew: EEW):
      print(f"地震速報！預估規模{eew.earthquake.mag}")
    ```
  - `update_eew`：更新現存的速報資料，主程式偵測到速報資料更新時，會呼叫該函式並傳入更新後的速報資料
    ```py
    async def update_eew(self, eew: EEW):
      print(f"地震速報更新！第{eew.serial}報，預估規模{eew.earthquake.mag}")
    ```
  - `lift_eew`：解除速報（通常會於速報發送後的4分鐘解除，視API來源），主程式呼叫該函式時會傳入欲解除警報的速報
    ```py
    async def lift_eew(self, eew: EEW):
      print(f"地震速報{eew.id}解除")
    ```
  - `run`：啟動客戶端
    ```py
    async def run(self):
      print("自訂通知客戶端已啟動")
    ```
    如果該部分不需執行任何操作，則填寫`pass`即可：
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
  **歡迎將您開發的自訂通知客戶端發PR合併至主要分支，讓支持這個專案的大家能使用到更廣泛、多元且強大的功能！**
