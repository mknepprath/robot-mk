import os
import random
import re
import sys
from htmlentitydefs import name2codepoint as n2c
from datetime import datetime
import tweepy
import markov
from local_settings import *

class TwitterAPI:
    def __init__(self):
        consumer_key = os.environ.get('MY_CONSUMER_KEY')
        consumer_secret = os.environ.get('MY_CONSUMER_SECRET')
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        access_token = os.environ.get('MY_ACCESS_TOKEN_KEY')
        access_token_secret = os.environ.get('MY_ACCESS_TOKEN_SECRET')
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth, wait_on_rate_limit=True)

    def tweet(self, message):
        self.api.update_status(status=message)

    def reply(self, message, tweet_id):
        self.api.update_status(status=message, in_reply_to_status_id=tweet_id, auto_populate_reply_metadata=True)

def entity(text):
    if text[:2] == '&#':
        try:
            if text[:3] == '&#x':
                return unichr(int(text[3:-1], 16))
            else:
                return unichr(int(text[2:-1]))
        except ValueError:
            pass
    else:
        guess = text[1:-1]
        numero = n2c[guess]
        try:
            text = unichr(numero)
        except KeyError:
            pass
    return text

def filter_tweet(tweet):
    tweet.full_text = re.sub(r'\b(RT|MT) .+', '', tweet.full_text) #take out anything after RT or MT
    tweet.full_text = re.sub(
        r'(\#|@|(h\/t)|(http))\S+',
        '',
        tweet.full_text
    ) #Take out URLs, hashtags, hts, etc.
    tweet.full_text = re.sub(r'\n', '', tweet.full_text) #take out new lines.
    tweet.full_text = re.sub(r'\"|\(|\)', '', tweet.full_text) #take out quotes.
    htmlsents = re.findall(r'&\w+;', tweet.full_text)
    if len(htmlsents) > 0:
        for item in htmlsents:
            tweet.full_text = re.sub(item, entity(item), tweet.full_text)
    tweet.full_text = re.sub(r'\xe9', 'e', tweet.full_text) #take out accented e
    return tweet.full_text

def grab_tweets(twitter, max_id=None):
    source_tweets = []
    user_tweets = twitter.api.user_timeline(
        screen_name=user,
        count=200,
        max_id=max_id,
        tweet_mode='extended'
    )
    max_id = user_tweets[len(user_tweets)-1].id-1
    for tweet in user_tweets:
        if tweet.full_text[0][0] != '@':
            tweet.full_text = filter_tweet(tweet)
            if len(tweet.full_text) != 0:
                source_tweets.append(tweet.full_text)
    return source_tweets, max_id

def grab_replies(twitter, max_id=None):
    source_replies = []
    user_replies = twitter.api.user_timeline(
        screen_name=user,
        count=200,
        max_id=max_id,
        tweet_mode='extended'
    )
    max_id = user_replies[len(user_replies)-1].id-1
    for tweet in user_replies:
        if tweet.full_text[0][0] == '@':
            tweet.full_text = filter_tweet(tweet)
            if len(tweet.full_text) != 0:
                source_replies.append(tweet.full_text)
    return source_replies, max_id

if __name__ == '__main__':
    twitter = TwitterAPI()
    if not DEBUG:
        guess = random.choice(range(ODDS))
    else:
        guess = 0

    currentHour = datetime.now().hour
    awake = currentHour <= 3 or currentHour >= 11
    print ('TWEET O\'CLOCK') if awake else 'sleepin'

    if guess == 0 and awake:
        #gets tweets
        source_tweets = []
        for handle in SOURCE_ACCOUNTS:
            user = handle
            max_id = None
            for x in range(17)[1:]:
                source_tweets_iter, max_id = grab_tweets(twitter, max_id)
                source_tweets += source_tweets_iter
            print '{0} tweets found in {1}'.format(len(source_tweets), handle)
            if len(source_tweets) == 0:
                print 'Error fetching tweets from Twitter. Aborting.'
                sys.exit()
        mine = markov.MarkovChainer(ORDER)
        for tweet in source_tweets:
            if re.search('([\.\!\?\"\']$)', tweet):
                pass
            else:
                tweet += '.'
            mine.add_text(tweet)

        for x in range(0, 10):
            ebook_tweet = mine.generate_sentence()

        #randomly drop the last word, as Horse_ebooks appears to do.
        if random.randint(0, 4) == 0 and re.search(r'(in|to|from|for|with|by|our|of|your|around|under|beyond)\s\w+$', ebook_tweet) != None:
            print 'Losing last word randomly'
            ebook_tweet = re.sub(r'\s\w+.$', '', ebook_tweet)
            print ebook_tweet

        #if a tweet is very short, this will randomly add a second sentence to it.
        if ebook_tweet != None and len(ebook_tweet) < 40:
            rando = random.randint(0, 10)
            if rando == 0 or rando == 7:
                print 'Short tweet. Adding another sentence randomly'
                newer_tweet = mine.generate_sentence()
                if newer_tweet != None:
                    ebook_tweet += ' ' + mine.generate_sentence()
                else:
                    ebook_tweet = ebook_tweet
            elif rando == 1:
                #say something crazy/prophetic in all caps
                print 'ALL THE THINGS'
                ebook_tweet = ebook_tweet.upper()

        #throw out tweets that match anything from the source account.
        if ebook_tweet != None and len(ebook_tweet) < 240:
            for tweet in source_tweets:
                if ebook_tweet[:-1] not in tweet:
                    continue
                else:
                    print 'TOO SIMILAR: ' + ebook_tweet
                    sys.exit()

            #throw out tweets that end with 'by on' or similar
            dribbbletweets = ['by on', 'BY ON', 'by for on']
            if any(d in ebook_tweet for d in dribbbletweets):
                print 'DRIBBBLE TWEET: ' + ebook_tweet
                sys.exit()

            if not DEBUG:
                twitter.tweet(ebook_tweet)

            print 'Tweeted \'' + ebook_tweet + '\''

        elif ebook_tweet is None:
            print 'Tweet is empty, sorry.'
        else:
            print 'TOO LONG: ' + ebook_tweet
    else:
        print str(guess) + ' No, sorry, not this time.' #message if the random number fails.

    source_mentions = twitter.api.mentions_timeline(count=2)
    for mention in source_mentions:
        if random.choice(range(FAVE_ODDS)) == 0 and awake:
            if not twitter.api.get_status(id=mention.id).favorited:
                twitter.api.create_favorite(id=mention.id)
                print 'Favorited \'' + mention.text + '\''

    for mention in source_mentions:
        source_compare_tweets = twitter.api.user_timeline(
            screen_name='robot_mk',
            count=50)
        mentioned = False
        for tweet in source_compare_tweets:
            if tweet.in_reply_to_status_id == mention.id:
                print 'Already replied to this one.'
                mentioned = True
        if random.choice(range(REPLY_ODDS)) == 0 and awake and not mentioned:

            source_replies = []
            for handle in SOURCE_ACCOUNTS:
                user = handle
                max_id = None
                for x in range(17)[1:]:
                    source_replies_iter, max_id = grab_replies(twitter, max_id)
                    source_replies += source_replies_iter
                print '{0} replies found in {1}'.format(len(source_replies), handle)
                if len(source_replies) == 0:
                    print 'Error fetching replies from Twitter. Aborting.'
                    sys.exit()
            mine = markov.MarkovChainer(ORDER)
            for reply in source_replies:
                if re.search('([\.\!\?\"\']$)', reply):
                    pass
                else:
                    reply += '.'
                mine.add_text(reply)

            for x in range(0, 10):
                ebook_reply = mine.generate_sentence()

            rando = random.randint(0, 10)
            if rando == 0:
                #say something crazy/prophetic in all caps
                print 'ALL THE THINGS'
                ebook_reply = ebook_reply.upper()

            #throw out tweets that match anything from the source account.
            if ebook_reply != None and len(ebook_reply) < 240:
                #reply
                if random.choice(range(QUOTE_ODDS)) == 0:
                    ebook_reply += ' http://twitter.com/' + mention.user.screen_name + '/status/' + str(mention.id)
                    twitter.reply(ebook_reply, mention.id)
                    print 'Quoted with \'' + ebook_reply + '\''
                else:
                    twitter.reply(ebook_reply, mention.id)
                    print 'Replied with \'' + ebook_reply + '\''
