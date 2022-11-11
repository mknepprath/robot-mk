import os
import random
import re
import sys
from datetime import datetime

import requests
import tweepy
from openai import api_key
from openai.api_resources.completion import Completion
from openai.api_resources.image import Image

from local_settings import *

api_key = os.environ.get("OPENAI_API_KEY")

DELIMITER = "\n#########\n"
DEBUG_RESPONSE = {
    'choices': [
        {
            'text': 'I\'m sorry, I\'m not sure what you mean.\nOk!\nmknepprath:Ok!'
        }
    ]
}


class TwitterAPI:
    def __init__(self):
        consumer_key = os.environ.get('MY_CONSUMER_KEY')
        consumer_secret = os.environ.get('MY_CONSUMER_SECRET')
        access_token = os.environ.get('MY_ACCESS_TOKEN_KEY')
        access_token_secret = os.environ.get('MY_ACCESS_TOKEN_SECRET')

        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)

        self.api = tweepy.API(auth, wait_on_rate_limit=True)

    def tweet(self, status):
        self.api.update_status(status=status)

    def reply(self, status, in_reply_to_status_id):
        self.api.update_status(
            status=status, in_reply_to_status_id=in_reply_to_status_id, auto_populate_reply_metadata=True)

    def upload_media(self, filename):
        media_response = self.api.media_upload(filename=filename)
        return media_response

    def create_media_metadata(self, media_id, alt_text):
        self.api.create_media_metadata(media_id, alt_text=alt_text)

    def tweet_with_media(self, status, media_id):
        self.api.update_status(status=status, media_ids=[media_id])


def filter_out(string, substr):
    return [str for str in string if
            not any(sub in str for sub in substr) and not str.startswith("@")]


def filter_out_replies(string, substr):
    return [str for str in string if
            not any(sub in str for sub in substr) and str.startswith("@")]


def get_tweets(twitter, screen_name, max_id=None):
    # Gets tweets from the specified account's timeline.

    # Instatiates tweets list.
    source_tweets = []
    source_replies = []

    # Gets raw tweets from timeline.
    user_tweets = twitter.api.user_timeline(
        screen_name=screen_name,
        count=200,
        max_id=max_id,
        tweet_mode='extended'
    )

    # Gets the ID of the last tweet returned.
    max_id = user_tweets[len(user_tweets)-1].id - 1

    # Loops through all returned tweets.
    for tweet in user_tweets:
        # If the tweet has a length less than 0, skip.
        if len(tweet.full_text) != 0:

            # If the tweet is not a reply, append to source_tweets.
            if tweet.in_reply_to_status_id_str == None:
                source_tweets.append(tweet.full_text)

            # If the tweet is a reply, append to source_replies.
            else:
                source_replies.append(tweet.full_text)

    return source_tweets, source_replies, max_id


def main():
    twitter = TwitterAPI()

    if not DEBUG:
        guess = random.choice(range(ODDS))
        reply_guess = random.choice(range(REPLY_ODDS))
        image_guess = random.choice(range(IMAGE_ODDS))
    else:
        guess = 0
        reply_guess = 0
        image_guess = 1

    # Checks the current time before tweeting. This bot sleps.
    current_hour = datetime.now().hour
    # 4 hour difference.
    # Awake if the current hour is greater than 11pm (3) and less than 7am (11).
    if DEBUG:
        awake = True
    else:
        awake = not (current_hour > 3 and current_hour < 11)
        awake = True
    if awake:
        print("I'm awake. " + str(current_hour) + ":00")
    else:
        print("I'm asleep. " + str(current_hour) + ":00")

    # Instantiates empty tweets list.
    source_tweets = []
    source_replies = []

    if (guess == 0 or reply_guess == 0) and awake:
        print('Fetching tweets...')
        # Populates tweets list.
        for screen_name in SOURCE_ACCOUNTS:
            # Reset max_id for each account.
            max_id = None

            # Gets a bunch of tweets.
            for x in range(4)[1:]:
                source_tweets_iter, source_replies_iter, max_id = get_tweets(
                    twitter, screen_name, max_id)
                source_tweets += source_tweets_iter
                source_replies += source_replies_iter
            print('{0} tweets and {1} replies found in @{2}.'.format(
                len(source_tweets), len(source_replies), screen_name))

            if len(source_tweets) == 0:
                print('Error fetching tweets from Twitter. Aborting.')
                sys.exit()

    if guess == 0 and awake:
        print('\nGenerating tweets...')

        if not DEBUG:
            filtered_source_tweets = filter_out(
                source_tweets, ["RT", "https://t.co"])
            random.shuffle(filtered_source_tweets)
            response = Completion.create(
                engine="davinci",
                prompt=DELIMITER.join(filtered_source_tweets[:30]) + "." + DELIMITER, temperature=0.9,
                max_tokens=50,
                frequency_penalty=0,
                presence_penalty=0.6,
                stop=[DELIMITER]
            )
        else:
            response = DEBUG_RESPONSE

        print('OpenAI candidates:')
        print(response['choices'][0]['text'])
        openai_tweet = response['choices'][0]['text'].split(DELIMITER)[
            0].strip()
        # Remove t.co links. Twitter blocks 'em.
        openai_tweet = re.sub(r"https:\/\/t.co\S+",
                              "[outgoing link]", openai_tweet)

        # Replace mention with link.
        openai_tweet = openai_tweet.replace("@", "https://twitter.com/")

        # If the tweet exists, and it's not too long, and it isn't tweeting at someone...
        if openai_tweet != None and len(openai_tweet) < 240:
            if not DEBUG:
                if (openai_tweet != ''):
                    if image_guess == 0:
                        print('\nAdding an image...')
                        response = Image.create(
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

                            media_response = twitter.upload_media(
                                filename=filename)
                            # twitter.create_media_metadata(
                            #     media_response.media_id, alt_text=alt_text)
                            twitter.tweet_with_media(
                                status=openai_tweet, media_id=media_response.media_id)
                            print('Tweeted \'' + openai_tweet + '\' with image.')

                            os.remove(filename)
                        else:
                            print("Unable to download image")
                    else:
                        twitter.tweet(openai_tweet)
                        print('Tweeted \'' + openai_tweet + '\'.')
                else:
                    print('No status to tweet.')
            else:
                print('Didn\'t tweet \'' + openai_tweet +
                      '\' because DEBUG is True.')

        elif openai_tweet is None:
            print('Tweet is empty, sorry.')
        else:
            print('BAD TWEET: ' + openai_tweet)

    else:
        # Message if the random number fails.
        if DEBUG:
            print(str(guess) + ' No, sorry, not this time.')

    if reply_guess == 0 and awake:
        # Let's do stuff with mentions. First, let's get a couple. Note: This means
        # that the bot will only reply to the most recent two mentions.
        source_mentions = twitter.api.mentions_timeline(
            count=2, tweet_mode='extended')

        print('\nGetting last two mentions.')

        # Loop through the two mentions.
        for mention in source_mentions:
            # Only do this while awake, sometimes.
            if random.choice(range(FAVE_ODDS)) == 0 and awake:
                # If the mention isn't favorited, favorite it.
                if not twitter.api.get_status(id=mention.id).favorited:
                    twitter.api.create_favorite(id=mention.id)
                    print('\nFavorited \'' + mention.full_text + '\'')

            # Start building prompt.
            mention_text_no_handles = re.sub(
                r'(@)\S+',
                '',
                mention.full_text).strip()
            prompt = mention.user.screen_name + \
                ":" + mention_text_no_handles + DELIMITER

            if mention.in_reply_to_status_id_str is not None:
                replied_to_tweet = mention
                while True:
                    if replied_to_tweet.in_reply_to_status_id_str is None:
                        break
                    else:
                        replied_to_tweet = twitter.api.get_status(
                            id=replied_to_tweet.in_reply_to_status_id, tweet_mode='extended')
                        replied_to_tweet_text_no_handles = re.sub(
                            r'(@)\S+',
                            '',
                            replied_to_tweet.full_text).strip()
                        prompt = replied_to_tweet.user.screen_name + \
                            ":" + replied_to_tweet_text_no_handles + DELIMITER + prompt
                        continue

            reply_source_tweets = filter_out_replies(
                source_tweets, ["RT", "https://t.co"])
            random.shuffle(reply_source_tweets)

            # Starts the prompt with some context for the bot.
            # The following is a conversation with an AI assistant. The assistant is helpful, creative, clever, and very friendly.
            prompt = "Other replies by " + TWEET_ACCOUNT + ":\n\n" + DELIMITER.join(reply_source_tweets[:20]) + DELIMITER + "\nThe following is a conversation with " + TWEET_ACCOUNT + ", a Twitter bot. " + TWEET_ACCOUNT + " was created by Michael Knepprath. " + TWEET_ACCOUNT + " is happy and friendly.\n\n" + \
                prompt + TWEET_ACCOUNT + ":"

            print("\nPrompt:")
            print(prompt)
            print("===\n")

            # Instantiate replied to false.
            replied = False

            # Get tweets from this bot to see it's already replied to the mentions.
            bot_tweets = twitter.api.user_timeline(
                screen_name=TWEET_ACCOUNT,
                count=150,
                tweet_mode='extended',
            )

            # Check if the current mention matches a tweet this bot has replied to.
            for tweet in bot_tweets:
                if tweet.in_reply_to_status_id == mention.id:
                    print('Matches a tweet bot has replied to: \'' +
                          tweet.full_text + '\'')
                    replied = True

            # If the bot is awake and has not replied to this mention, reply, sometimes.
            if awake and not replied:
                print('Generating replies...\n')

                if not DEBUG:
                    response = Completion.create(
                        engine="davinci",
                        prompt=prompt,
                        temperature=0.9,
                        max_tokens=50,
                        frequency_penalty=0,
                        presence_penalty=0.6,
                        stop=[DELIMITER]
                    )
                else:
                    response = DEBUG_RESPONSE

                print('OpenAI candidates:')
                print(response["choices"][0]["text"])
                openai_reply = response["choices"][0]["text"].split(DELIMITER)[
                    0].strip()
                # Remove t.co links. Twitter blocks 'em.
                openai_reply = re.sub(
                    r"https:\/\/t.co\S+", "[outgoing link]", openai_reply)

                # OpenAI prompts inlude a delimiter between lines, but sometimes forgets.
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
                if openai_reply != None and len(openai_reply) < 240 and "##" not in openai_reply:
                    # Reply.
                    if random.choice(range(QUOTE_ODDS)) == 0:
                        openai_reply += ' http://twitter.com/' + \
                            mention.user.screen_name + \
                            '/status/' + str(mention.id)
                        if not DEBUG:
                            twitter.tweet(openai_reply)
                            print('Quoted with \'' + openai_reply + '\'')
                        else:
                            print('Didn\'t quote \'' + openai_reply +
                                  '\' because DEBUG is True.')
                    else:
                        if not DEBUG:
                            twitter.reply(openai_reply, mention.id)
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
