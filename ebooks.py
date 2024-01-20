import os
import random
import re
import sys
from datetime import datetime, date
from html.parser import HTMLParser

from mastodon import Mastodon
import requests
import openai
import pprint as pp

from local_settings import *

DELIMITER = "\n##====##\n"
DEBUG_RESPONSE = {
    'choices': [
        {
            'text': 'I\'m sorry, I\'m not sure what you mean.\nOk!\nmknepprath:Ok!'
        }
    ]
}


class HTMLFilter(HTMLParser):
    text = ""

    def handle_data(self, data):
        self.text += data


def filter_out(string, substr):
    return [s for s in string if
            not any(sub in s for sub in substr) and not s.startswith("@")]


def filter_out_replies(string, substr):
    return [s for s in string if
            not any(sub in s for sub in substr) and s.startswith("@")]


def get_tweets(mastodon, max_id=None):
    # Gets tweets from the specified account's timeline.

    # Instantiates tweets list.
    source_tweets = []
    source_replies = []

    user_tweets = mastodon.account_statuses(
        id=SOURCE_ID,
        limit=200,
        max_id=max_id
    )

    # Gets the ID of the last tweet returned.
    max_id = user_tweets[len(user_tweets) - 1].id - 1

    # Loops through all returned tweets.
    for tweet in user_tweets:
        # If the tweet has a length less than 0, skip.
        if len(tweet.content) != 0:

            f = HTMLFilter()
            f.feed(tweet.content)

            # If the tweet is not a reply, append to source_tweets.
            if tweet.in_reply_to_id is None:
                source_tweets.append(f.text)

            # If the tweet is a reply, append to source_replies.
            else:
                source_replies.append(f.text)

    return source_tweets, source_replies, max_id


def main():
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    mastodon = Mastodon(
        api_base_url='https://mastodon.social',
        client_id=os.environ.get('MASTODON_CLIENT_KEY'),
        client_secret=os.environ.get('MASTODON_CLIENT_SECRET'),
        access_token=os.environ.get('MASTODON_ACCESS_TOKEN'),
    )

    if not DEBUG:
        guess = random.choice(range(ODDS))
        reply_guess = random.choice(range(REPLY_ODDS))
        image_guess = random.choice(range(IMAGE_ODDS))
    else:
        guess = 0
        reply_guess = 0
        image_guess = 1

    # Checks the current time before tweeting. This bot sleeps.
    current_hour = datetime.now().hour
    # 4-hour difference.
    # Awake if the current hour is greater than 11pm (3) and less than 7am (11).
    if DEBUG:
        awake = True
    else:
        awake = not (3 < current_hour < 11)
    if awake:
        print("I'm awake. " + str(current_hour) + ":00")
    else:
        print("I'm asleep. " + str(current_hour) + ":00")

    awake = True

    # Instantiates empty tweets list.
    source_tweets = []
    source_replies = []

    if (guess == 0 or reply_guess == 0) and awake:
        print('Fetching posts...')
        # Populates tweets list.
        # Reset max_id for account. TODO: This might be doing nothing.
        max_id = None

        # Gets a bunch of tweets.
        for _ in range(4)[1:]:
            source_tweets_iter, source_replies_iter, max_id = get_tweets(
                mastodon, max_id)
            source_tweets += source_tweets_iter
            source_replies += source_replies_iter
        print('{0} posts and {1} replies found in @mknepprath.'.format(
            len(source_tweets), len(source_replies)))

        if len(source_tweets) == 0:
            print('Error fetching tweets from Twitter. Aborting.')
            sys.exit()

    if guess == 0 and awake:
        print('\nGenerating tweets...')

        if not DEBUG:
            filtered_source_tweets = filter_out(
                source_tweets, ["RT", "https://", "@"])
            filtered_source_tweets.reverse()
            random.shuffle(filtered_source_tweets)

            prompt = "Example posts:\n\n" + DELIMITER.join(filtered_source_tweets[:30]) + "." + DELIMITER \
                     + "\n\nNext micro-post tangential to or similar to one of the topics above:"
            system = "It is currently " + date.today().strftime("%b-%d-%Y") + ". You generate new short posts based " \
                                                                              "on a list of posts authored by " \
                                                                              "Michael Knepprath."

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": system
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=60,
                n=1,
                stop=[DELIMITER]
            )
        else:
            response = DEBUG_RESPONSE

        print('OpenAI candidates:')
        print(response['choices'])
        print("")
        openai_tweet = response['choices'][0]['message']['content'].strip()
        # Remove the delimiter.
        openai_tweet = openai_tweet.replace("##====##", "").strip()

        # Remove t.co links. Twitter blocks 'em.
        # openai_tweet = re.sub(r"https:\/\/t.co\S+",
        #                       "[outgoing link]", openai_tweet)

        # Replace mention with link.
        # openai_tweet = openai_tweet.replace("@", "https://twitter.com/")

        # If the tweet exists, and it's not too long, and it isn't tweeting at someone...
        if openai_tweet is not None and len(openai_tweet) < 480:
            if not DEBUG:
                if openai_tweet != '':
                    if image_guess == 0:
                        print('\nAdding an image...')
                        response = openai.Image.create(
                            prompt=openai_tweet,
                            n=1,
                            size="512x512"
                        )
                        image_url = response['data'][0]['url']
                        # alt_text = response['data'][0]['alt_text']
                        filename = "/tmp/temp.png"
                        request = requests.get(image_url, stream=True)
                        if request.status_code == 200:
                            with open(filename, 'wb') as image:
                                for chunk in request:
                                    image.write(chunk)

                            # Mastodon media post
                            mastodon_media_response = mastodon.media_post(
                                filename,
                                description='I\'m a bot, sorry'
                            )
                            if mastodon_media_response.id:
                                mastodon.status_post(
                                    status=openai_tweet,
                                    media_ids=[mastodon_media_response.id]
                                )
                            print('Posted \'' + openai_tweet + '\' with image.')

                            os.remove(filename)
                        else:
                            print("Unable to download image")
                    else:
                        # Mastodon post
                        mastodon.status_post(status=openai_tweet)
                        print('Posted \'' + openai_tweet + '\'.')
                else:
                    print('No status to post.')
            else:
                print('Didn\'t post \'' + openai_tweet +
                      '\' because DEBUG is True.')

        elif openai_tweet is None:
            print('Post is empty, sorry.')
        else:
            print('BAD POST: ' + openai_tweet)

    else:
        # Message if the random number fails.
        if DEBUG:
            print(str(guess) + ' No, sorry, not this time.')

    if reply_guess == 0 and awake:
        # Let's do stuff with mentions. First, let's get a couple. Note: This means
        # that the bot will only reply to the most recent two mentions.
        source_mentions = mastodon.notifications(types=["mention"], limit=2)

        print('\nGetting last two mentions.')

        # Loop through the two mentions.
        for mention in source_mentions:

            messages = []

            # Only do this while awake, sometimes.
            if random.choice(range(FAVE_ODDS)) == 0 and awake:
                # If the mention isn't favorited, favorite it.
                if not mention.status.favourited:
                    mastodon.status_favourite(id=mention.status.id)
                    print('\nFavorited \'' + mention.status.content + '\'')

            f = HTMLFilter()
            f.feed(mention.status.content)

            # Start building prompt.
            mention_text_no_handles = re.sub(
                r'(@)\S+',
                '',
                f.text
            ).strip()

            messages.insert(0, {
                "role": "user" if mention.account.acct == "robot_mk" else "assistant",
                "content": mention_text_no_handles
            })
            prompt = mention.account.acct + ":" + mention_text_no_handles + DELIMITER

            if mention.status.in_reply_to_id is not None:
                replied_to_tweet = mention.status
                while True:
                    if replied_to_tweet.in_reply_to_id is None:
                        break
                    else:
                        replied_to_tweet = mastodon.status(id=replied_to_tweet.in_reply_to_id)
                        f = HTMLFilter()
                        f.feed(replied_to_tweet.content)
                        replied_to_tweet_text_no_handles = re.sub(
                            r'(@)\S+',
                            '',
                            f.text).strip()
                        messages.insert(0, {
                            "role": "user" if replied_to_tweet.account.acct == "robot_mk" else "assistant",
                            "content": replied_to_tweet_text_no_handles
                        })
                        prompt = replied_to_tweet.account.acct + \
                                 ":" + replied_to_tweet_text_no_handles + DELIMITER + prompt
                        continue

            reply_source_tweets = filter_out_replies(
                source_tweets, ["RT", "https://t.co"])
            random.shuffle(reply_source_tweets)

            # Starts the prompt with some context for the bot. The following is a conversation with an AI assistant.
            # The assistant is helpful, creative, clever, and very friendly.
            system = "Example reply posts by Michael Knepprath:\n\n" + DELIMITER.join(reply_source_tweets[:20]) \
                     + DELIMITER + "\nThe following is a conversation with a human man named Michael Knepprath."
            messages.insert(0, {
                "role": "system",
                "content": system
            })
            messages.append({
                "role": "user",
                "content": "What do you think I, Michael Knepprath, would say next? You were given examples of how I "
                           "talk. Reply with just that message. It will not be a question. It may be weird. It may be "
                           "off-topic. Do not include placeholder text, make your best guess:"
            })
            prompt = prompt + BOT_ACCOUNT + ":"

            print("\nPrompt:")
            print(prompt)
            print("===\n")
            print("\nMessages:")
            pp.pprint(messages)
            print("===\n")

            # Instantiate replied to false.
            replied = False

            # Get tweets from this bot to see it's already replied to the mentions.
            bot_tweets = mastodon.account_statuses(
                id=BOT_ID,
                limit=150
            )

            # Check if the current mention matches a tweet this bot has replied to.
            for tweet in bot_tweets:
                if tweet.in_reply_to_id == mention.status.id:
                    f = HTMLFilter()
                    f.feed(tweet.content)
                    print('Matches a tweet bot has replied to: \'' +
                          f.text + '\'')
                    replied = True

            # If the bot is awake and has not replied to this mention, reply, sometimes.
            if awake and not replied:
                print('Generating replies...\n')

                if not DEBUG:
                    response = openai.ChatCompletion.create(
                        model="gpt-4",
                        messages=messages,
                        max_tokens=60,
                        n=1,
                        stop=[DELIMITER]
                    )
                else:
                    response = DEBUG_RESPONSE

                print('OpenAI candidates:')
                print(response["choices"][0]["message"])
                openai_reply = response["choices"][0]["message"]["content"].split(DELIMITER)[
                    0].strip()
                # Remove t.co links. Twitter blocks 'em.
                openai_reply = re.sub(
                    r"https:\/\/t.co\S+", "[outgoing link]", openai_reply)

                # OpenAI prompts include a delimiter between lines, but sometimes forgets.
                # If this happens, we can detect it and remove the extra lines.
                split_by_lines = openai_reply.split("\n")
                if len(split_by_lines) > 1:
                    bad_line_index: int = -1
                    for i in range(len(split_by_lines)):
                        if split_by_lines[i].split(" ")[0].find(":") != -1:
                            bad_line_index = i
                            break
                    if bad_line_index != -1:
                        openai_reply = "\n".join(
                            split_by_lines[:bad_line_index])

                # Checks if the reply exists, is less than the allowable tweet
                # length and doesn't contain a partial delimiter value.
                if openai_reply is not None and len(openai_reply) < 240 and "##" not in openai_reply:
                    # Reply.
                    # FIXME: Disabling quote, not supported by Mastodon at the moment.
                    # if random.choice(range(QUOTE_ODDS)) == 0:
                    #     if not DEBUG:
                    #         mastodon.status_post(status=openai_reply, quote_id=mention.status.id)
                    #         print('Quoted with \'' + openai_reply + '\'')
                    #     else:
                    #         print('Didn\'t quote \'' + openai_reply +
                    #               '\' because DEBUG is True.')
                    # else:
                    if not DEBUG:
                        mastodon.status_post(status=openai_reply, in_reply_to_id=mention.status.id)
                        print('Replied with \'' + openai_reply + '\'')
                    else:
                        print('Didn\'t reply \'' + openai_reply +
                              '\' because DEBUG is True.')
            else:
                print('Not replying this time.')
    else:
        # Message if the random number fails.
        if DEBUG:
            print(str(reply_guess) + ' No reply this time.')


if __name__ == '__main__':
    main()
