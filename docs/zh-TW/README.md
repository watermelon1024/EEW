# EEW

 [![Contributors][contributors-shield]][contributors-url]
 [![Forks][forks-shield]][forks-url]
 [![Stargazers][stars-shield]][stars-url]
 [![Issues][issues-shield]][issues-url]
 [![License][license-shield]][license-url]

 [contributors-shield]: https://img.shields.io/github/contributors/watermelon1024/EEW.svg?style=for-the-badge
 [contributors-url]: https://github.com/watermelon1024/EEW/graphs/contributors

 [forks-shield]: https://img.shields.io/github/forks/watermelon1024/EEW.svg?style=for-the-badge
 [forks-url]: https://github.com/watermelon1024/EEW/network/members

 [stars-shield]: https://img.shields.io/github/stars/watermelon1024/EEW.svg?style=for-the-badge
 [stars-url]: https://github.com/watermelon1024/EEW/stargazers

 [issues-shield]: https://img.shields.io/github/issues/watermelon1024/EEW.svg?style=for-the-badge
 [issues-url]: https://github.com/watermelon1024/EEW/issues

 [license-shield]: https://img.shields.io/github/license/watermelon1024/EEW.svg?style=for-the-badge
 [license-url]: https://github.com/watermelon1024/EEW/blob/main/LICENSE

 [English](https://github.com/watermelon1024/EEW/blob/main/README.md) | [繁體中文](https://github.com/watermelon1024/EEW/blob/main/docs/zh-TW/README.md)

 ---

 一個簡單、強大、免費且易於擴充的地震預警通知系統！

 ---

 此專案使用由 [ExpTech 探索科技](https://exptech.com.tw) 提供的 API，請遵照其[服務條款](https://exptech.com.tw/tos)。

 *注意：此專案目前仍處於測試版本。*

# 安裝
 **需要 Python 3.8 或更高的版本**

 ### 1. 下載專案
 首先下載專案的源代碼，可以使用以下的指令取得：
 ```bash
 git clone https://github.com/watermelon1024/EEW.git
 cd EEW
 ```

 ### 2. 使用虛擬環境 (可選，但強烈建議使用)
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
 根據 `.env.example` 的格式編輯 `.env` 檔案，並填入所需的環境變數。\
 例如:
 ```toml
 DISCORD_BOT_TOKEN=  # Discord 機器人金鑰

 LINEBOT_ACCESS_TOKEN=  # Line 機器人 Access Token
 LINEBOT_CHANNEL_SECRET=  # Line 機器人 Channel Secret
 ```

 ### 4. 編輯配置
 根據 `config.toml.example` 的格式編輯 `config.toml` 檔案，並根據自身需求填入設定所需的值。\
 例如:
 ```toml
 # 設定
 debug-mode = false  # 除錯模式

 [discord-bot]
 channels = [
     { id = 123456789, mention = "everyone" },  # 提及所有人 (@everyone)
     { id = 456789123, mention = 6543219870 },  # 提及 ID 為 `6543219870` 的身分組
     { id = 987654321 },  # 不提及
 ]

 [line-bot]
 channels = [
     "abcdefgh...",
     "ijklmnop...",
 ]  # 使用者或是群組 ID

 [log]
 retention = 30  # 日誌保存的天數
 format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"  # 日誌輸出格式
 ```

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

# 自訂通知客戶端
 如果你沒有找到想使用的現成客戶端，你可以為你自己建立客製化的通知客戶端！\
 請見[開發文檔](https://github.com/watermelon1024/EEW/blob/main/docs/zh-TW/dev/notification.md)。

## 特別感謝
 [Littlecatowo](https://github.com/Littlecatowo) 協助翻譯
