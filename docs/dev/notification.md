# 自訂通知客戶端
  請遵照`src/notification/template.py`的格式，撰寫下方內容

## 開發客戶端功能
  實作客戶端的相關函式：

  (注意：下方範例皆是宣告於 class 中的函式，故第一個傳入參數為 `self`)
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

  注意：請將這些函式宣告為協程(coroutine)，也就是使用`async def`宣告，且避免使用阻塞呼叫(blocking calls)
  
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

  然而，若無可避免地需要使用阻塞呼叫，請善用線程函式庫：
  ```py
  import threading

  async def run(self):
    thread = threading.Thread(target=start_func)
    thread.run()
  ```

## 註冊客戶端
  客戶端功能撰寫完成後，請創建一個`register`函式將其註冊到主程式中：
  ```py
  def register(config: Config, logger: Logger):
    return CustomNotificationClient(...)
  ```
  主程式在呼叫該註冊函式時，會傳入記錄器(`logger`)和設定(`config`)參數，為了正確地取得設定參數，請在檔案中宣告`NAMESPACE`常數，代表該客戶端的設定檔區間

  例如：假設你在設定檔中的命名空間為`custom-client`：
  ```toml
  # 其他設定

  [custom-client]
  debug = true
  channel = "123456789"
  # 其他客戶端的設定
  ```
  那麼，你的`custom_client.py`中的`NAMESPACE`值就應該宣告為`custom-client`
  ```py
  class CustomNotificationClient(NotificationClient):
    ...

  NAMESPACE = "custom-client"

  def register(config: Config, logger: Logger):
    debug_mode = config["debug"]
    notification_channel = config["channel"]
    ...
    return CustomNotificationClient(logger, debug_mode, notification_channel, ...)
  ```

# 一同貢獻
  **歡迎將您開發的自訂通知客戶端發PR合併至主要分支，讓支持這個專案的大家能使用到更廣泛、多元且強大的功能！**
