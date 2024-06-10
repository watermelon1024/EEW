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

 [>English<](https://github.com/watermelon1024/EEW/blob/main/README.md) | [繁體中文](https://github.com/watermelon1024/EEW/blob/main/docs/README/README-zh-TW.md)

 ---

 A simple, powerful, free, and easily extensible earthquake early warning notify system.

 ---

 This project uses the API provided by [Exptech](https://exptech.com.tw). Please adhere to their [Terms of Service](https://exptech.com.tw/tos).

 *Note: This project is currently a beta version.*

# Installing
 **Python 3.8 or higher is required**

 ### 1. Download the Project
 First, download the source code of the project. You can obtain the project's source code by:
 ```bash
 git clone https://github.com/watermelon1024/EEW.git
 cd EEW
 ```

 ### 2. Use a Virtual Environment (Optional but Recommended)
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
 Then, activate the virtual environment
 ```bash
 # Windows
 venv\Scripts\activate

 # Linux/macOS
 source venv/bin/activate
 ```

 ### 3. Set Up Environment Variables
 Rename the `.env.example` file to `.env` and fill in the required values for each environment variable according to your configuration.

 `.env.example`:
 ```
 DISCORD_BOT_TOKEN=  # discord bot token
 ```

 ### 4. Edit the Configuration
 Rename the `config.toml.example` file to `config.toml` and fill in the required values for each configuration according to your demand.

 ### 5. Install Dependencies
 Install the dependencies required for the project.
 ```bash
 pip install -r requirements.txt
 ```

 ### 6. Run the Project
 Once the dependencies are installed and the environment variables are set up, you can run the project!
 ```bash
 python main.py
 ```
