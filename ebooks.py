import os
import random
import re
import sys
from htmlentitydefs import name2codepoint
from datetime import datetime
import tweepy
import markov
from local_settings import *


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
    max_id = user_tweets[len(user_tweets)-1].id-1

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
    awake = current_hour <= 3 or current_hour >= 11
    print 'TWEET O\'CLOCK! Fetching tweets.' if awake else 'slepin.'

    # Instantiates empty tweets list.
    source_tweets = []
    source_replies = []

    if guess == 0 and awake:
        # Populates tweets list.
        for screen_name in SOURCE_ACCOUNTS:
            # Reset max_id for each account.
            max_id = None

            # Gets a bunch of tweets.
            for x in range(17)[1:]:
                source_tweets_iter, source_replies_iter, max_id = get_tweets(
                    twitter, screen_name, max_id)
                source_tweets += source_tweets_iter
                source_replies += source_replies_iter
            print '{0} tweets and {1} replies found in @{2}.'.format(len(source_tweets), len(source_replies), screen_name)
            if len(source_tweets) == 0:
                print 'Error fetching tweets from Twitter. Aborting.'
                sys.exit()

    if guess == 0 and awake:
        print 'Generating tweets.'

        mine = markov.MarkovChainer()

        # If the tweet doesn't end with punctuation, add a period.
        for tweet in source_tweets:
            if re.search('([\.\!\?\"\']$)', tweet):
                pass
            else:
                tweet += '.'
            mine.add_text(tweet)

        for x in range(0, 10):
            ebook_tweet = mine.generate_sentence()

        # randomly drop the last word, as Horse_ebooks appears to do.
        if random.randint(0, 4) == 0 and re.search(r'(in|to|from|for|with|by|our|of|your|around|under|beyond)\s\w+$', ebook_tweet) != None:
            print 'Losing last word randomly.'
            ebook_tweet = re.sub(r'\s\w+.$', '', ebook_tweet)
            print ebook_tweet

        # If a tweet is very short, this will randomly add a second sentence to it.
        if ebook_tweet != None and len(ebook_tweet) < 40:
            # Get random number.
            random_int = random.randint(0, 10)

            # 1/5 chance of adding another tweet to tweet.
            if random_int < 3:
                print 'Short tweet. Randomly adding another sentence.'
                next_ebook_tweet = mine.generate_sentence()

                # If the new tweet has text, add the text.
                if next_ebook_tweet != None:
                    ebook_tweet += ' ' + next_ebook_tweet

            # 1/10 chance of uppercasing tweet.
            elif random_int == 2:
                # say something crazy/prophetic in all caps.
                print 'ALL THE THINGS'
                ebook_tweet = ebook_tweet.upper()

        # throw out tweets that match anything from the source account.
        if ebook_tweet != None and len(ebook_tweet) < 240:
            for tweet in source_tweets:
                if ebook_tweet[:-1] not in tweet:
                    continue
                else:
                    print 'TOO SIMILAR: ' + ebook_tweet
                    sys.exit()

            if not DEBUG:
                twitter.tweet(ebook_tweet)

            print 'Tweeted \'' + ebook_tweet + '\'.'

        elif ebook_tweet is None:
            print 'Tweet is empty, sorry.'
        else:
            print 'TOO LONG: ' + ebook_tweet
    else:
        # Message if the random number fails.
        print str(guess) + ' No, sorry, not this time.'

    # Let's do stuff with mentions. First, let's get a couple.
    source_mentions = twitter.api.mentions_timeline(count=2)

    print 'Getting last two mentions.'

    # Loop through the two mentions.
    for mention in source_mentions:
        # Only do this while awake, sometimes.
        if random.choice(range(FAVE_ODDS)) == 0 and awake:
            # If the mention isn't favorited, favorite it.
            if not twitter.api.get_status(id=mention.id).favorited:
                twitter.api.create_favorite(id=mention.id)
                print 'Favorited \'' + mention.text + '\''

        # Get tweets from this bot.
        source_compare_tweets = twitter.api.user_timeline(
            screen_name='robot_mk',
            count=50)

        # Instantiate replied to false.
        replied = False

        # Check if the current mention matches a tweet this bot has replied to.
        for tweet in source_compare_tweets:
            if tweet.in_reply_to_status_id == mention.id:
                print 'Matches a tweet bot has replied to.'
                replied = True

        # If the bot is awake and has not replied to this mention, reply, sometimes.
        if random.choice(range(REPLY_ODDS)) == 0 and awake and not replied:
            print 'Generating replies.'

            mine = markov.MarkovChainer()

            for reply in source_replies:
                if re.search('([\.\!\?\"\']$)', reply):
                    pass
                else:
                    reply += '.'
                mine.add_text(reply)

            for x in range(0, 10):
                ebook_reply = mine.generate_sentence()

            if random.randint(0, 10) == 0:
                # Say something crazy/prophetic in all caps.
                print 'ALL THE THINGS'
                ebook_reply = ebook_reply.upper()

            # Throw out tweets that match anything from the source account.
            if ebook_reply != None and len(ebook_reply) < 240 and not DEBUG:
                # Reply.
                if random.choice(range(QUOTE_ODDS)) == 0:
                    ebook_reply += ' http://twitter.com/' + \
                        mention.user.screen_name + '/status/' + str(mention.id)
                    twitter.tweet(ebook_reply)
                    print 'Quoted with \'' + ebook_reply + '\''
                else:
                    twitter.reply(ebook_reply, mention.id)
                    print 'Replied with \'' + ebook_reply + '\''
