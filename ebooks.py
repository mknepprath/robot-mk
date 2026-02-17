import os
import random
import re
import sys
from datetime import datetime, date
from html.parser import HTMLParser

from mastodon import Mastodon
import requests
import anthropic
import pprint

from local_settings import *

DELIMITER = "\n#########\n"
DEBUG_RESPONSE = {
    'content': 'I\'m sorry, I\'m not sure what you mean.\nOk!\nmknepprath:Ok!'
}

# Coffee-related terms to filter out for excessive coffee posting
COFFEE_TERMS = [
    'coffee', 'cappuccino', 'latte', 'espresso', 'caffeine', 'barista', 
    'brew', 'brewing', 'roast', 'beans', 'grind', 'grinding', 'americano',
    'mocha', 'frappuccino', 'cold brew', 'iced coffee', 'macchiato'
]


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


def contains_excessive_coffee(text, threshold=0.3):
    """Check if text contains too many coffee references"""
    if not text:
        return False
    
    words = text.lower().split()
    coffee_count = sum(1 for word in words if any(term in word for term in COFFEE_TERMS))
    
    # If more than 30% of words are coffee-related, consider it excessive
    return len(words) > 0 and (coffee_count / len(words)) > threshold


def filter_coffee_heavy_posts(posts, max_coffee_ratio=0.15):
    """Filter out posts that are too coffee-heavy from training data"""
    filtered_posts = []
    coffee_posts = []
    
    for post in posts:
        if contains_excessive_coffee(post):
            coffee_posts.append(post)
        else:
            filtered_posts.append(post)
    
    # Allow some coffee posts but limit them
    max_coffee_posts = max(1, int(len(posts) * max_coffee_ratio))
    if coffee_posts:
        filtered_posts.extend(random.sample(coffee_posts, min(len(coffee_posts), max_coffee_posts)))
    
    return filtered_posts


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
    # Initialize Claude API client
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )
    
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
            
            # Apply coffee filtering to reduce excessive coffee posting
            filtered_source_tweets = filter_coffee_heavy_posts(filtered_source_tweets)
            random.shuffle(filtered_source_tweets)

            # Enhanced prompt for better Michael Knepprath mimicry
            examples_text = DELIMITER.join(filtered_source_tweets[:30])
            
            system_prompt = f"""You are Michael Knepprath (@mknepprath), a creative technologist, designer, and developer. 

Your writing style characteristics:
- Thoughtful observations about technology, design, and creativity
- Often shares insights about web development, UI/UX, and digital products
- Has a warm, conversational tone that's informative but approachable
- Sometimes philosophical about the intersection of technology and humanity
- Enjoys wordplay and clever observations
- Occasionally shares personal moments but keeps them relatable
- Not overly promotional or salesy
- Uses proper grammar and punctuation
- Rarely posts excessively about any single topic (like coffee)

Today's date: {date.today().strftime("%b-%d-%Y")}

Based on the writing style in the examples below, generate a new authentic post that sounds like Michael would naturally write it. Focus on his interests in design, technology, creativity, or thoughtful observations about digital life."""

            user_prompt = f"""Here are recent posts by Michael Knepprath:

{examples_text}

Please write one new post in Michael's authentic voice and style. Keep it under 400 characters, natural and engaging, avoiding excessive focus on any single topic. Do not include the delimiter."""

            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=100,
                    system=system_prompt,
                    messages=[{
                        "role": "user", 
                        "content": user_prompt
                    }]
                )
                claude_response = {"content": response.content[0].text}
            except Exception as e:
                print(f"Error calling Claude API: {e}")
                claude_response = DEBUG_RESPONSE
        else:
            claude_response = DEBUG_RESPONSE

        print('Claude candidates:')
        print(claude_response['content'])
        print("")
        claude_tweet = claude_response['content'].strip()
        
        # Remove the delimiter if it somehow got included
        claude_tweet = claude_tweet.replace(DELIMITER, "").strip()
        
        # Additional check: reject if the generated post is too coffee-heavy
        if contains_excessive_coffee(claude_tweet, threshold=0.4):
            print(f'Generated post too coffee-heavy, skipping: {claude_tweet}')
            claude_tweet = None

        # If the tweet exists, and it's not too long, and it isn't tweeting at someone...
        if claude_tweet is not None and len(claude_tweet) < 480:
            if not DEBUG:
                if claude_tweet != '':
                    if image_guess == 0:
                        print('\nSkipping image generation for now (Claude doesn\'t have DALL-E equivalent)...')
                        # TODO: Could integrate with other image generation services if needed
                    
                    # Mastodon post
                    mastodon.status_post(status=claude_tweet)
                    print('Posted \'' + claude_tweet + '\'.')
                else:
                    print('No status to post.')
            else:
                print('Didn\'t post \'' + claude_tweet +
                      '\' because DEBUG is True.')

        elif claude_tweet is None:
            print('Post is empty or filtered out, sorry.')
        else:
            print('BAD POST: ' + claude_tweet)

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

            # Start building conversation context.
            mention_text_no_handles = re.sub(
                r'(@)\S+',
                '',
                f.text
            ).strip()

            conversation = []
            current_message = {
                "role": "user",
                "content": mention_text_no_handles
            }
            conversation.append(current_message)

            # Build conversation thread if this is a reply
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

                        role = "assistant" if replied_to_tweet.account.acct == "robot_mk" else "user"
                        conversation.insert(0, {
                            "role": role,
                            "content": replied_to_tweet_text_no_handles
                        })

            reply_source_tweets = filter_out_replies(
                source_tweets, ["RT", "https://t.co"])
            random.shuffle(reply_source_tweets)

            # Enhanced system prompt for replies
            reply_examples = DELIMITER.join(reply_source_tweets[:20])
            system_prompt = f"""You are Michael Knepprath (@mknepprath), responding to a conversation. 

Your reply style:
- Thoughtful and engaging responses
- Builds on the conversation naturally  
- Maintains your voice: knowledgeable about tech/design but approachable
- Sometimes adds helpful insights or asks follow-up questions
- Keeps responses conversational, not overly formal
- Often connects topics to broader themes about technology, creativity, or design

Here are examples of your actual replies:
{reply_examples}

Respond as Michael would, staying true to his conversational style and interests."""

            print("\nConversation context:")
            pprint.pprint(conversation)
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
                    try:
                        response = client.messages.create(
                            model="claude-3-5-sonnet-20241022",
                            max_tokens=100,
                            system=system_prompt,
                            messages=conversation
                        )
                        claude_response = {"content": response.content[0].text}
                    except Exception as e:
                        print(f"Error calling Claude API for reply: {e}")
                        claude_response = DEBUG_RESPONSE
                else:
                    claude_response = DEBUG_RESPONSE

                print('Claude candidates:')
                print(claude_response["content"])
                claude_reply = claude_response["content"].strip()
                
                # Remove any delimiter artifacts
                claude_reply = claude_reply.split(DELIMITER)[0].strip()
                
                # Remove t.co links. Twitter blocks 'em.
                claude_reply = re.sub(
                    r"https:\/\/t.co\S+", "[outgoing link]", claude_reply)

                # Clean up any formatting artifacts
                split_by_lines = claude_reply.split("\n")
                if len(split_by_lines) > 1:
                    bad_line_index: int = -1
                    for i in range(len(split_by_lines)):
                        if split_by_lines[i].split(" ")[0].find(":") != -1:
                            bad_line_index = i
                            break
                    if bad_line_index != -1:
                        claude_reply = "\n".join(
                            split_by_lines[:bad_line_index])

                # Checks if the reply exists, is less than the allowable length 
                # and doesn't contain delimiter artifacts.
                if claude_reply and len(claude_reply) < 240 and DELIMITER not in claude_reply:
                    if not DEBUG:
                        mastodon.status_post(status=claude_reply, in_reply_to_id=mention.status.id)
                        print('Replied with \'' + claude_reply + '\'')
                    else:
                        print('Didn\'t reply \'' + claude_reply +
                              '\' because DEBUG is True.')
                else:
                    print('Reply rejected - too long, empty, or contains artifacts')
            else:
                print('Not replying this time.')
    else:
        # Message if the random number fails.
        if DEBUG:
            print(str(reply_guess) + ' No reply this time.')


if __name__ == '__main__':
    main()