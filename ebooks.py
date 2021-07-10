import os
import random
import re
import sys
from datetime import datetime
import openai
import tweepy
from local_settings import *

openai.api_key = os.environ.get("OPENAI_API_KEY")

DELIMITER = "\n---\n"
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


if __name__ == '__main__':
    twitter = TwitterAPI()

    if not DEBUG:
        guess = random.choice(range(ODDS))
        reply_guess = random.choice(range(REPLY_ODDS))
    else:
        guess = 0
        reply_guess = 0

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

        if not DEBUG:
            random.shuffle(source_tweets)
            response = openai.Completion.create(engine="davinci", prompt=DELIMITER.join(
                source_tweets[:30]) + "." + DELIMITER, max_tokens=50)
        else:
            response = DEBUG_RESPONSE

        print('OpenAI candidates:')
        print(response['choices'][0]['text'])
        openai_tweet = response['choices'][0]['text'].split(DELIMITER)[
            0].strip()
        # Remove t.co links. Twitter blocks 'em.
        openai_tweet = re.sub(r"https:\/\/t.co\S+", "", openai_tweet)

        if openai_tweet != None and len(openai_tweet) < 240:
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

            # Starts the prompt with some context for the bot.
            prompt = TWEET_ACCOUNT + ":My name is Robot MK, I'm a twitter bot. I am friendly and happy. Let's chat!" + \
                DELIMITER + prompt + TWEET_ACCOUNT + ":"

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
            if (random.choice(range(4)) == 0 or DEBUG) and awake and not replied:
                print('Generating replies...\n')

                if not DEBUG:
                    response = openai.Completion.create(
                        engine="davinci", prompt=prompt, max_tokens=50)
                else:
                    response = DEBUG_RESPONSE

                print('OpenAI candidates:')
                print(response["choices"][0]["text"])
                openai_reply = response["choices"][0]["text"].split(DELIMITER)[
                    0].strip()
                # Remove t.co links. Twitter blocks 'em.
                openai_reply = re.sub(r"https:\/\/t.co\S+", "", openai_reply)

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

                if openai_reply != None and len(openai_reply) < 240:
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
