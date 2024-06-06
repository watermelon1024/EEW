# EEW
 Earthquake Early Warning

 [English](https://github.com/watermelon1024/EEW/blob/main/README.md) | [繁體中文](https://github.com/watermelon1024/EEW/blob/main/docs/README/README-zh-TW.md)

 此專案使用由 [Exptech](https://exptech.com.tw) 提供的API，請遵照其[服務條款](https://exptech.com.tw/tos)!

 *注意： 此專案目前還是測試版本*

# 安裝
 **需要 Python 3.8 或更高的版本**

 ### 1. 下載專案
 首先下載專案的源代碼，可以使用以下的指令取得：
 ```bash
 git clone https://github.com/watermelon1024/EEW.git
 cd EEW
 ```

 ### 2. 使用虛擬環境 (推薦使用)
 在安裝專案之前，建議使用虛擬環境來隔離專案的依賴套件，以避免和其他專案的依賴套件衝突。
 #### 使用 Python 內建的虛擬環境套件
 ```bash
 python -m venv venv
 ```
 #### 使用第三方虛擬環境管理工具
 ```bash
 pip install virtualenv

 virtualenv venv
 ```
 接著，啟用虛擬環境：
 ```bash
 # Windows
 venv\Scripts\activate

 # Linux/macOS
 source venv/bin/activate
 ```

 ### 3. 設置環境變數
 將 `.env.example` 檔案重新命名為 `.env`，並根據設定填入所需的環境變數。

 `.env.example`:
 ```
 DISCORD_BOT_TOKEN=  # Discord 機器人金鑰
 ```

 ### 4. 編輯配置
 將 `config.toml.example` 重新命名為 `config.toml`，並根據自身需求填入各配置所需的值。

 ### 5. 安裝套件
 下載專案所需要的依賴套件。
 ```bash
 pip install -r requirements.txt
 ```

 ### 6. 執行專案
 安裝套件並設定環境變數後，即可執行專案！
 ```bash
 python main.py
 ```

## 特別感謝
 [Littlecatowo](https://github.com/Littlecatowo) 協助翻譯
