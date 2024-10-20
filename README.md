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

 <div align="center">
  <a href="https://github.com/watermelon1024/EEW">
   <img src="/asset/logo.png" alt="EEW" width="30%"/>
  </a>
 </div>

 [English](/README.md) | [繁體中文](/docs/zh-TW/README.md)

 ---

 A simple, powerful, free, and easily extensible multi-platform earthquake early warning notification system!

 ---

> [!IMPORTANT]
> This project uses the API provided by [ExpTech](https://exptech.com.tw). Please adhere to their [Terms of Service](https://exptech.com.tw/tos).

> [!NOTE]
> This project is currently in beta, and may undergo significant changes.

# Installing
 **Python 3.8 or higher is required**

 ### 1. Download the Project
 First, download the source code of the project. You can obtain the project's source code by:
 ```bash
 git clone https://github.com/watermelon1024/EEW.git
 cd EEW
 ```

 ### 2. Use a Virtual Environment (Optional but Strongly Recommended)
 Before installing the project, it's recommended to use a virtual environment to isolate the project's dependencies and prevent conflicts with dependencies of other projects.
 #### Using Python's Built-in Virtual Environment Module
 ```bash
 python -m venv venv
 ```
 #### Using a Third-Party Virtual Environment Management Tool
 ```bash
 pip install virtualenv

 virtualenv venv
 ```
 Then, activate the virtual environment:
 ```bash
 # Windows
 venv\Scripts\activate

 # Linux/macOS
 source venv/bin/activate
 ```

 ### 3. Set Up Environment Variables
 Edit the `.env` file according to the format in `.env.example` and fill in the required environment variables.\
 For example:
 ```toml
 DISCORD_BOT_TOKEN=  # Discord bot token

 LINEBOT_ACCESS_TOKEN=  # Line bot access token
 LINEBOT_CHANNEL_SECRET=  # Line bot channel secret
 ```

 ### 4. Edit the Configuration
 Edit the `config.toml` file according to the format in `config.toml.example` and fill in the required values based on your needs.\
 For example:
 ```toml
 # configuration
 debug-mode = false  # debug mode

 [discord-bot]
 channels = [
     { id = 123456789, mention = "everyone" },  # mention everyone (@everyone)
     { id = 456789123, mention = 6543219870 },  # mention the role with ID `6543219870`
     { id = 987654321 },  # no mention
 ]

 [line-bot]
 channels = [
     "abcdefgh...",
     "ijklmnop...",
 ]  # user or group IDs

 [log]
 retention = 30  # days of logs to keep
 format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>"  # log output format
 ```

 ### 5. Install Dependencies
 Install the required dependencies for the project.
 ```bash
 pip install -r requirements.txt
 ```

 ### 6. Run the Project
 After installing the dependencies and setting the environment variables, you can run the project!
 ```bash
 python main.py
 ```


# Bug Report & Issues

If you encounter any issues or have questions about the project, please feel free to open an issue on the [GitHub Issues page][issues-url].

1. Search through the existing issues to avoid duplicates.
2. Provide a clear and concise description of the problem, including steps to reproduce it.
3. Include any relevant logs or error messages.
4. Mention the environment (e.g., Python version, operating system) and configurations you are using.

Your feedback helps us improve the system for everyone!


# Custom Notification Client
If you haven't found an existing client that suits your needs, you can create a custom notification client for yourself!\
See also: [development documentation](/docs/en-US/dev/notification.md).
