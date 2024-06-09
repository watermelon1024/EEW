import os
from linebot.v3.messaging.configuration import Configuration
from linebot.v3.messaging import ApiClient
from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging import BroadcastRequest
from linebot.v3.messaging.rest import ApiException

config = Configuration(
    host="https://api.line.me",
)
config = Configuration(
    access_token=os.getenv("LINEBOT_ACCESS_TOKEN")
)

with ApiClient(config) as client:
    api = MessagingApi(client)
    broadcast_request = BroadcastRequest()

    try:   
        # api_response = api.broadcast(broadcast_request)
        api_response = api.broadcast("broadcast_request")

        print("The response of MessagingApi->broadcast:\n")
        print(api_response)
    except Exception as e:
        print("Exception when calling MessagingApi->broadcast: %s\n" % e)
