import os
import re
import json
import random
from dotenv import load_dotenv
from pyquery import PyQuery
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from influxdb import InfluxDBClient
from datetime import datetime, timedelta 
"""
init DB
"""
class DB():
    def __init__(self, ip, port, user, password, db_name):
        self.client = InfluxDBClient(ip, port, user, password, db_name) 
        self.client.create_database(db_name)
        print('Influx DB init.....')

    def insertData(self, data):
        """
        [data] should be a list of datapoint JSON,
        "measurement": means table name in db
        "tags": you can add some tag as key
        "fields": data that you want to store
        """
        if self.client.write_points(data):
            return True
        else:
            print('Falied to write data')
            return False

    def queryData(self, query):
        """
        [query] should be a SQL like query string
        """
        return self.client.query(query)

# Init a Influx DB and connect to it
db = DB('127.0.0.1', 8086, 'root', '', 'accounting_db')

load_dotenv() # Load your local environment variables


CHANNEL_TOKEN = os.environ.get('LINE_TOKEN')
CHANNEL_SECRET = os.getenv('LINE_SECRET')

app = FastAPI()

My_LineBotAPI = LineBotApi(CHANNEL_TOKEN) # Connect Your API to Line Developer API by Token
handler = WebhookHandler(CHANNEL_SECRET) # Event handler connect to Line Bot by Secret key

'''
For first testing, you can comment the code below after you check your linebot can send you the message below
'''
#CHANNEL_ID = os.getenv('LINE_UID') # For any message pushing to or pulling from Line Bot using this ID
# My_LineBotAPI.push_message(CHANNEL_ID, TextSendMessage(text='Welcome to my pokedex !')) # Push a testing message

# Events for message reply
my_event = ['#help', '#note', '#report', '#delete', '#sum']

'''
See more about Line Emojis, references below
> Line Bot Free Emojis, https://developers.line.biz/en/docs/messaging-api/emoji-list/
'''
# Create my emoji list
my_emoji = [
    [{'index':27, 'productId':'5ac1bfd5040ab15980c9b435', 'emojiId':'005'}],
    [{'index':27, 'productId':'5ac1bfd5040ab15980c9b435', 'emojiId':'019'}],
    [{'index':27, 'productId':'5ac1bfd5040ab15980c9b435', 'emojiId':'096'}]
]

# Line Developer Webhook Entry Point
@app.post('/')
async def callback(request: Request):
    body = await request.body() # Get request
    signature = request.headers.get('X-Line-Signature', '') # Get message signature from Line Server
    try:
        handler.handle(body.decode('utf-8'), signature) # Handler handle any message from LineBot and 
    except InvalidSignatureError:
        raise HTTPException(404, detail='LineBot Handle Body Error !')
    return 'OK'

# All message events are handling at here !
@handler.add(MessageEvent, message=TextMessage)
def handle_textmessage(event):
    global my_pokemons
    ''' Basic Message Reply
    message = TextSendMessage(text= event.message.text)
    My_LineBotAPI.reply_message(
        event.reply_token,
        message
    )
    '''
    # Split message by white space
    recieve_message = str(event.message.text).split(' ')
    # Get first splitted message as command
    case_ = recieve_message[0].lower().strip()
    # Case 1: Help command for listing all commands to user
    if re.match(my_event[0], case_):
        if len(recieve_message)!=1:
            My_LineBotAPI.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="Input error ! Enter #help for hint !"
                )
            )
            return
        command_describtion = '$ Commands:\n\
        #note [event] [+/-] [money]\n\t--> Accounting !\n\
        #report \n\t--> Show current billing !\n\
        #delete [item] \n\t--> Delete a piece of information !\n\
        #sum [time shift] \n\t--> Settle consumption for a certain time interval !\n'
        My_LineBotAPI.reply_message(
            event.reply_token,
            TextSendMessage(
                text=command_describtion,
                emojis=[
                    {
                        'index':0,
                        'productId':'5ac21a18040ab15980c9b43e',
                        'emojiId':'110'
                    }
                ]
            )
        )

    #note
    elif re.match(my_event[1], case_):
        # cmd: #note [事件] [+/-] [錢]
        if len(recieve_message)!=4:
            My_LineBotAPI.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="Input error ! Enter #help for hint !"
                )
            )
            return
        event_ = recieve_message[1]
        op = recieve_message[2]
        money = int(recieve_message[3])
        # process +/-
        if op == '-':
            money *= -1
        # get user id
        user_id = event.source.user_id
        
        # build data
        data = [
            {
                "measurement" : "accounting_items",
                "tags": {
                    "user": str(user_id),
                    "event_tag" : str(event_)
                },
                "fields":{
                    "event": str(event_),
                    "money": money
                }
            }
        ]
        if db.insertData(data):
            # successed
            My_LineBotAPI.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="Write to DB Successfully!"
                )
            )

    #report
    elif re.match(my_event[2], case_):
        # get user id
        if len(recieve_message)!=1:
            My_LineBotAPI.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="Input error ! Enter #help for hint !"
                )
            )
            return
        user_id = event.source.user_id
        query_str = """
        select * from accounting_items 
        """
        result = db.queryData(query_str)
        points = result.get_points(tags={'user': str(user_id)})
        
        reply_text = ''
        for i, point in enumerate(points):
            time = point['time']
            event_ = point['event']
            money = point['money']
            reply_text += f'[{i}] -> [{time}] : {event_}   {money}\n'

        My_LineBotAPI.reply_message(
            event.reply_token,
            TextSendMessage(
                text=reply_text
            )
        )

    #delete
    elif re.match(my_event[3], case_):
        if len(recieve_message)!=2:
            My_LineBotAPI.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="Input error ! Enter #help for hint !"
                )
            )
            return
        # get user id
        user_id = event.source.user_id
        event_ = recieve_message[1]

        query_1 = "DELETE FROM accounting_items WHERE event_tag="+"'"+event_+"'"
        db.queryData(query_1)

        My_LineBotAPI.reply_message(
            event.reply_token,
            TextSendMessage(
                text="Delete sucessfully"
            )
        )

    #sum
    elif re.match(my_event[4], case_):
        if len(recieve_message)!=2:
            My_LineBotAPI.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="Input error ! Enter #help for hint !"
                )
            )
            return
        day_ = recieve_message[1]
        user_id = event.source.user_id
        try:
            query_str = "select * from accounting_items where time>=now()-"+str(day_)
            print(query_str)
            result = db.queryData(query_str)
        except:
            My_LineBotAPI.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="Should input what 'd', ex:#sum 1d !"
                )
                )
        else:
            points = result.get_points(tags={'user': str(user_id)})
            sum = 0
            reply_text = ''
            for i, point in enumerate(points):
                sum = sum + point['money']

            My_LineBotAPI.reply_message(
                event.reply_token,
                TextSendMessage(
                     text="sum :"+str(sum)
             )
         )

    else:
        My_LineBotAPI.reply_message(
            event.reply_token,
            TextSendMessage(
                text="Input error ! Enter #help for hint !"
            )
        )

# Line Sticker Class
class My_Sticker:
    def __init__(self, p_id: str, s_id: str):
        self.type = 'sticker'
        self.packageID = p_id
        self.stickerID = s_id

'''
See more about Line Sticker, references below
> Line Developer Message API, https://developers.line.biz/en/reference/messaging-api/#sticker-message
> Line Bot Free Stickers, https://developers.line.biz/en/docs/messaging-api/sticker-list/
'''
# Add stickers into my_sticker list
my_sticker = [My_Sticker(p_id='446', s_id='1995'), My_Sticker(p_id='446', s_id='2012'),
     My_Sticker(p_id='446', s_id='2024'), My_Sticker(p_id='446', s_id='2027'),
     My_Sticker(p_id='789', s_id='10857'), My_Sticker(p_id='789', s_id='10877'),
     My_Sticker(p_id='789', s_id='10881'), My_Sticker(p_id='789', s_id='10885'),
     ]

# Line Sticker Event
@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    # Random choice a sticker from my_sticker list
    ran_sticker = random.choice(my_sticker)
    # Reply Sticker Message
    My_LineBotAPI.reply_message(
        event.reply_token,
        StickerSendMessage(
            package_id= ran_sticker.packageID,
            sticker_id= ran_sticker.stickerID
        )
    )
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app='main:app', reload=True, host='0.0.0.0', port=8787)