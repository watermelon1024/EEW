import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, MessageEvent, TextMessage
from linebot.exceptions import InvalidSignatureError

host="https://api.line.me"
access_token=os.getenv("LINEBOT_ACCESS_TOKEN")

linebot_api = LineBotApi(access_token)
handler = WebhookHandler(os.getenv("LINEBOT_CHANNEL_SECRET"))

groupid ={
    "bot": "Cf7c26d34ee6c4b6680923b2652617d47",
}

message = TextSendMessage(text="搖哦")
linebot_api.push_message(groupid['bot'],messages=message)

app = Flask(__name__)

# @app.route("/", methods=["POST"])
# def callback():
#     signature = request.headers["X-Line-Signature"]
#     body = request.get_data(as_text=True)
#     app.logger.info(f"Request body: {body}")
#     try:
#         handler.handle(body, signature)
#     except InvalidSignatureError:
#         abort(400)
#     return "OK"

# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event):
#     group_id = event.source.group_id
#     user_id = event.source.user_id
#     print(f"群組 ID: {group_id}")
#     print(f"使用者 ID: {user_id}")

#     # 回應訊息
#     linebot_api.reply_message(
#         event.reply_token,
#         TextSendMessage(text=f"群組 ID 是: {group_id}")
#     )

# if __name__ == "__main__":
#     app.run()