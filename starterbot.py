import os
import time
import re
from slackclient import SlackClient
from pymongo import MongoClient
import json

with open('config.json', 'r') as f:
    data = f.read()
config = json.loads(data)

slack_client = SlackClient(config['SLACK_BOT_TOKEN'])
starterbot_id = None

RTM_READ_DELAY = 1
EXAMPLE_COMMAND = "do"
SCOREBOARD_COMMAND = "scoreboard"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

connection = MongoClient(config['db_url'], config['db_port'])
db = connection[config['db_name']]
db.authenticate(config['db_user'], config['db_pass'])

score = db.score

def parse_bot_commands(slack_events):
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"], event["user"]
    return None, None, None

def parse_direct_mention(message_text):
    matches = re.search(MENTION_REGEX, message_text)
    return (matches.group(1), matches.group(2).strip()) if matches else ("", "")

def get_user_info(user_id):
    return slack_client.api_call(
        "users.info",
        user=user_id,
        include_locale=True,
    )

def handle_scoreboard(command, channel, author):
    user_id, message = parse_direct_mention(command.partition(SCOREBOARD_COMMAND)[2].strip())
    userinfo = get_user_info(user_id)
    authorinfo = get_user_info(author)
    tokens = message.split()
    if len(tokens) > 0:
        try:
            amount = float(tokens[0])
            description = " ".join(tokens[1:]) if len(tokens) > 1 else ""
            entity = {
                "giver": authorinfo["user"],
                "receiver": userinfo["user"],
                "amount": amount,
                "description": description 
            }
            score.insert(entity)
            return "%s has given %.2f points to %s for %s" % (authorinfo["user"]["real_name"], amount, userinfo["user"]["real_name"], description)
        except:
            return "Syntax: @User <amount> <description>"
    else:
        message = "```%-20s %s\n" % ("User", "Score")
        for x in score.aggregate([ {"$group": { "_id": "$receiver.id", "total": { "$sum": "$amount" }, "name": { "$first": "$receiver.real_name" } } }]):
            message += "%-20s %.2f\n" % (x["name"], x["total"])
        return message + "```"

def handle_command(command, channel, author):
    default_response = "Not sure what you mean. Try *{}*.".format(EXAMPLE_COMMAND)
    response = None
    if command.startswith(EXAMPLE_COMMAND):
        response = "Sure...write some more code then I can do that!"
    elif command.startswith(SCOREBOARD_COMMAND):
        response = handle_scoreboard(command, channel, author)

    slack_client.api_call(
        "chat.postMessage",
        channel=channel,
        text=response or default_response
    )

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel, user = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel, user)
                time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception tracebackc printed above.")

