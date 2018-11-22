import os
import time
import re
from slackclient import SlackClient

slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))
starterbot_id = None

RTM_READ_DELAY = 1
EXAMPLE_COMMAND = "do"
SCOREBOARD_COMMAND = "scoreboard"
MENTION_REGEX = "^<@(|[WU].+?)>(.*)"

def parse_bot_commands(slack_events):
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"], event["user"]
    return None, None, None

def parse_direct_mention(message_text):
    matches = re.search(MENTION_REGEX, message_text)
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None, None)

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
    return "The user mentioned is: " + userinfo["user"]["real_name"] + \
           ". \nThe message is: " + message +\
           ". \nThe author is " + authorinfo["user"]["real_name"]

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

