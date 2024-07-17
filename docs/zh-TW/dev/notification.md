# 自訂通知客戶端
  
  你有兩種方式可以製作你自訂客戶端：
  1. 單獨檔案\
    在`notification/`下建立你自己的python檔案(即`notification/your_client.py`)，並遵照`src/notification/template/main.py`的格式，撰寫[下方](#開發客戶端功能)內容

  2. 包裝成模組(module)\
    在`notification/`下創建一個資料夾，你可以盡情的在裡面寫你的自訂客戶端，內部結構由你自行決定，只需在第一層建立`register.py`檔案(即`notification/your_client/register.py`)，並在裡面定義全局常數`NAMESPACE`和`register`函式即可(見[註冊客戶端](#註冊客戶端))

  注意：若有使用到額外的第三方函式庫(package)，請不要將相關的函式庫進行全局導入(將`import`語句放置於開頭或全域空間)，而是於`register`函式內再行導入，以避免在讀取`NAMESPACE`時因無法導入該函式庫而產生錯誤。

## 開發客戶端功能
  實作客戶端的相關函式：\
  只需宣告要接收的事件，若不需要，則不用宣告\
  (注意：下方範例皆是宣告於 class 中的函式，故第一個傳入參數皆為`self`)
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
  - `start`：啟動客戶端
    ```py
    async def start(self):
      print("自訂通知客戶端已啟動")
    ```

  注意：請將這些函式宣告為協程(coroutine)，也就是使用`async def`宣告，且避免使用阻塞呼叫(blocking calls)\
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

  class CustomNotificationClient(NotificationClient):
    def blocking_func(self):
      ...

    async def start(self):
      thread = threading.Thread(target=self.blocking_func)
      thread.run()
  ```

## 註冊客戶端
  客戶端功能撰寫完成後，請創建一個`register`函式將其註冊到主程式中：
  ```py
  def register(config: Config, logger: Logger):
    return CustomNotificationClient(...)
  ```
  主程式在呼叫該註冊函式時，會傳入記錄器(`logger`)和設定(`config`)參數，為了正確地取得設定參數，請在檔案中宣告`NAMESPACE`常數，代表該客戶端的設定檔區間\
  例如：假設你在設定檔中的命名空間為`custom-client`：
  ```toml
  # 其他設定

  [custom-client]
  debug = true
  channel = "123456789"
  # 其他客戶端的設定
  ```
  那麼，你的`custom_client.py`中的`NAMESPACE`值就應該宣告為`custom-client`：
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
