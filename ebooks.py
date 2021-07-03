import os
import openai
import random
import re
import sys
from datetime import datetime
import tweepy
from local_settings import *

openai.api_key = os.environ.get("OPENAI_API_KEY")

delimiter = "\n---\n"


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


def filter_tweet(tweet):
    # Removes things I don't want tweeted, like hashtags & links.

    # Take out anything after RT or MT.
    tweet.full_text = re.sub(r'\b(RT|MT) .+', '', tweet.full_text)

    # Take out URLs, hashtags, hts, etc.
    tweet.full_text = re.sub(
        r'(\#|(h\/t)|(http))\S+',
        '',
        tweet.full_text
    )
    # Take out any mentions. This is separated out so we can do something
    # smarter with it in the future.
    tweet.full_text = re.sub(
        r'(@)\S+',
        '',
        tweet.full_text
    )

    # Take out new lines.
    # tweet.full_text = re.sub(r'\n', '', tweet.full_text)

    # Take out quotes.
    tweet.full_text = re.sub(r'\"|\(|\)', '', tweet.full_text)

    return tweet.full_text


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
        # Filter tweet.
        tweet.full_text = filter_tweet(tweet)

        # If the tweet has a length less than 0, skip.
        if len(tweet.full_text) != 0:

            # If the tweet is not a reply, append to source_tweets.
            if tweet.in_reply_to_status_id_str == None:
                source_tweets.append(tweet.full_text)

            # If the tweet is a reply, append to source_replies.
            else:
                source_replies.append(tweet.full_text)

    return source_tweets, source_replies, max_id


if __name__ == '__main__':
    twitter = TwitterAPI()

    if not DEBUG:
        guess = random.choice(range(ODDS))
    else:
        guess = 0

    # Checks the current time before tweeting. This bot sleps.
    current_hour = datetime.now().hour
    awake = True
    if awake:
        print("I'm awake.")
    else:
        print("I'm asleep.")

    # Instantiates empty tweets list.
    source_tweets = []
    source_replies = []

    if guess == 0 and awake:
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

        response = openai.Completion.create(
            engine="davinci", prompt=delimiter.join(source_tweets[:80]) + "." + delimiter, max_tokens=50)
        print('OpenAI candidates:')
        print(response.choices[0].text)
        openai_tweet = response.choices[0].text.split(delimiter)[0].strip()

        # throw out tweets that match anything from the source account.
        if openai_tweet != None and len(openai_tweet) < 240:
            for tweet in source_tweets:
                if openai_tweet[:-1] not in tweet:
                    continue
                else:
                    print('TOO SIMILAR: ' + openai_tweet)
                    sys.exit()

            if not DEBUG:
                twitter.tweet(openai_tweet)
                print('Tweeted \'' + openai_tweet + '\'.')
            else:
                print('Didn\'t tweet \'' + openai_tweet +
                      '\' because DEBUG is True.')

        elif openai_tweet is None:
            print('Tweet is empty, sorry.')
        else:
            print('TOO LONG: ' + openai_tweet)

        # Let's do stuff with mentions. First, let's get a couple.
        source_mentions = twitter.api.mentions_timeline(count=2)

        print('\nGetting last two mentions.')

        # Get tweets from this bot.
        source_compare_tweets = twitter.api.user_timeline(
            screen_name='robot_mk',
            count=50)

        # Loop through the two mentions.
        for mention in source_mentions:
            # Only do this while awake, sometimes.
            if random.choice(range(FAVE_ODDS)) == 0 and awake:
                # If the mention isn't favorited, favorite it.
                if not twitter.api.get_status(id=mention.id).favorited:
                    twitter.api.create_favorite(id=mention.id)
                    print('\nFavorited \'' + mention.text + '\'')

            # Start building prompt.
            prompt = "robot_mk:My name is Robot MK, I'm a twitter bot." + delimiter
            prompt = prompt + mention.user.screen_name + ":" + mention.text + delimiter

            if mention.in_reply_to_status_id_str is not None:
                replied_to_tweet = mention
                while True:
                    if replied_to_tweet.in_reply_to_status_id_str is None:
                        break
                    else:
                        replied_to_tweet = twitter.api.get_status(
                            id=replied_to_tweet.in_reply_to_status_id)
                        prompt = replied_to_tweet.user.screen_name + \
                            ":" + replied_to_tweet.text + delimiter + prompt
                        continue

            prompt = prompt + "robot_mk:"

            print("\nPrompt:")
            print(prompt)
            print("===\n")

            # Instantiate replied to false.
            replied = False

            # Check if the current mention matches a tweet this bot has replied to.
            for tweet in source_compare_tweets:
                if tweet.in_reply_to_status_id == mention.id:
                    print('Matches a tweet bot has replied to.')
                    replied = True

            # If the bot is awake and has not replied to this mention, reply, sometimes.
            if random.choice(range(REPLY_ODDS)) == 0 and awake and not replied:
                print('Generating replies...')

                response = openai.Completion.create(
                    engine="davinci", prompt=prompt, max_tokens=50)
                print('OpenAI candidates:')
                print(response.choices[0].text)
                openai_reply = response.choices[0].text.split(delimiter)[
                    0].strip()
                print(openai_reply)

                # Throw out tweets that match anything from the source account.
                if openai_reply != None and len(openai_reply) < 240 and not DEBUG:
                    # Reply.
                    if random.choice(range(QUOTE_ODDS)) == 0:
                        reply = re.sub(
                            r'(@)\S+',
                            '',
                            openai_reply).strip()
                        reply += ' http://twitter.com/' + \
                            mention.user.screen_name + \
                            '/status/' + str(mention.id)
                        twitter.tweet(reply)
                        print('Quoted with \'' + reply + '\'')
                    else:
                        reply = re.sub(
                            r'(@)\S+',
                            '',
                            openai_reply).strip()
                        twitter.reply(reply, mention.id)
                        print('Replied with \'' + reply + '\'')
            else:
                print('Not replying this time.')
    else:
        # Message if the random number fails.
        print(str(guess) + ' No, sorry, not this time.')
