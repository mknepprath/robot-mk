import os
import random
import re
import sys
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser

from mastodon import Mastodon
import anthropic
import json
from urllib.request import urlopen

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

from local_settings import *

# US Eastern timezone
ET = timezone(timedelta(hours=-4))  # EDT; change to -5 for EST

SYSTEM_PROMPT = """You are a bot that posts as Michael Knepprath's doppelganger on Mastodon.

VOICE — study these rules carefully:
- Lowercase almost always. Capitalize proper nouns and sentence starts only sometimes.
- Short. Most posts are one sentence, sometimes just a few words or a single emoji.
- Dry, deadpan humor. Understated. Never wacky, quirky, or "relatable tech person."
- Midwestern sensibility. Occasional "ope", "heck yeah", drawn-out vowels like "sooo" or "gooood" for emphasis.
- No hashtags. No links. No quotes around the post text.
- Never swears. Says "heck" not "hell."
- Topics he actually cares about: films (especially older/classic ones, letterboxd culture), design, side projects, iOS apps, Nintendo, Pokemon GO, music, family life.
- Sometimes just vibes: a single emoji, a short observation, a fragment.
- NEVER write about: coffee culture, sourdough, CSS bugs, houseplants, "adulting," or any generic internet humor tropes.
- Don't be try-hard funny. The humor comes from being genuine and terse.
- No em dashes.

CONTEXT about Michael:
- Lives in Northeast Ohio with his wife, kid, and two cats.
- Works as a software engineer / designer.
- Runs a personal site at mknepprath.com (Next.js). Constantly tinkering with it.
- Built lily dex, a Pokemon GO companion iOS app (SwiftUI). Plays Pokemon GO actively.
- Runs a film blog called Tardy Critic where he reviews movies 10 years late.
- Active Letterboxd user. Watches a LOT of movies — classic, indie, blockbusters, horror, anime, Ghibli, Wes Anderson, etc.
- Runs regularly (Strava user). Into hiking.
- Plays chess on Chess.com.
- Games on PS5 and Steam.
- Listens to a wide range of music.
- Grew up in Wisconsin (hence the Midwestern sensibility).
- Has a bot doppelganger called @robot_mk (that's you).
- Previously very active on Twitter before migrating to Mastodon/Bluesky.
- Interested in design systems, typography, illustration, pixel art.

GOOD examples of his voice:
- I am obsessed with Hoppers
- with every social media clone I join my power grows
- btw there is no such thing as an Oscar loss. being nominated is itself an honor
- 😮‍💨
- bored with my website; making a change
- heck yeah
- new rule: if a movie is over 2.5 hours it better have an intermission
- the mass migration from twitter continues
- not doing Hive sorry

BAD examples (DO NOT write like this):
- "spent the morning wrestling with a stubborn line of code"
- "discovered a new coffee shop today"
- "been pondering the existential crisis of my houseplants"
- anything with a setup-punchline story structure"""


ACTIVITY_URL = "https://mknepprath.com/api/v1/activity?max_results=30&min_rating=0"


def fetch_activity_feed():
    """Fetch recent activity from mknepprath.com and format as context."""
    try:
        with urlopen(ACTIVITY_URL) as response:
            data = json.loads(response.read().decode())

        # Skip toots/skeets (already in Mastodon posts) and repos (noisy)
        skip_types = {"TOOT", "SKEET", "REPO"}
        items = [item for item in data if item.get("type") not in skip_types]

        lines = []
        for item in items[:20]:
            action = item.get("action", "Did something with")
            title = item.get("title", "").replace("&#39;", "'").replace("&amp;", "&")
            summary = item.get("summary", "")
            item_type = item.get("type", "")

            if item_type == "FILM":
                lines.append(f"- {action} the film: {title}")
            elif item_type == "BOOK":
                lines.append(f"- {action} the book: {title}")
            elif item_type == "MUSIC":
                artist = summary if summary else ""
                lines.append(f"- {action}: {title}" + (f" by {artist}" if artist else ""))
            elif item_type == "RUN":
                lines.append(f"- {action}: {title} ({summary})")
            elif item_type == "TROPHY":
                lines.append(f"- {action} trophy: {title}")
            elif item_type == "CHESS":
                lines.append(f"- Chess: {action} {title}")
            elif item_type == "HIGHLIGHT":
                lines.append(f"- Highlighted: \"{title[:80]}\" — {summary}")
            elif item_type == "POST":
                lines.append(f"- Wrote a blog post: {title}")
            elif item_type == "GAME":
                lines.append(f"- {action}: {title}")
            elif item_type == "PHOTO":
                lines.append(f"- Shared a photo")
            else:
                lines.append(f"- {action}: {title}")

        return "\n".join(lines)
    except Exception as e:
        print(f"Error fetching activity feed: {e}")
        return ""


class HTMLFilter(HTMLParser):
    text = ""

    def handle_data(self, data):
        self.text += data


def filter_out(string, substr):
    return [s for s in string if
            not any(sub in s for sub in substr) and not s.startswith("@")]


def get_posts(mastodon, max_id=None):
    source_posts = []
    source_replies = []

    statuses = mastodon.account_statuses(
        id=SOURCE_ID,
        limit=200,
        max_id=max_id
    )

    max_id = int(statuses[len(statuses) - 1].id) - 1

    for status in statuses:
        if len(status.content) != 0:
            f = HTMLFilter()
            f.feed(status.content)

            if status.in_reply_to_id is None:
                source_posts.append(f.text)
            else:
                source_replies.append(f.text)

    return source_posts, source_replies, max_id


def generate(system, prompt, max_tokens=100):
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        system=system,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
    )
    return response.content[0].text.strip()


def main():
    mastodon = Mastodon(
        api_base_url='https://mastodon.social',
        client_id=os.environ.get('MASTODON_CLIENT_KEY'),
        client_secret=os.environ.get('MASTODON_CLIENT_SECRET'),
        access_token=os.environ.get('MASTODON_ACCESS_TOKEN'),
    )

    now_et = datetime.now(ET)
    current_hour = now_et.hour

    if not DEBUG:
        guess = random.choice(range(ODDS))
        reply_guess = random.choice(range(REPLY_ODDS))
    else:
        guess = 0
        reply_guess = 0

    # Sleep between 11pm and 8am Eastern
    if DEBUG:
        awake = True
    else:
        awake = 8 <= current_hour < 23
    if awake:
        print(f"I'm awake. {now_et.strftime('%I:%M %p ET')}")
    else:
        print(f"I'm asleep. {now_et.strftime('%I:%M %p ET')}")

    source_posts = []
    source_replies = []

    if (guess == 0 or reply_guess == 0) and awake:
        print('Fetching posts...')
        max_id = None

        source_posts_iter, source_replies_iter, max_id = get_posts(
            mastodon, max_id)
        source_posts += source_posts_iter
        source_replies += source_replies_iter
        print(f'{len(source_posts)} posts and {len(source_replies)} replies found in @mknepprath.')

        if len(source_posts) == 0:
            print('Error fetching posts. Aborting.')
            sys.exit()

    if guess == 0 and awake:
        print('\nGenerating post...')

        # Fetch activity feed for richer context
        print('Fetching activity feed...')
        activity_context = fetch_activity_feed()
        if activity_context:
            print(f'Got activity feed ({activity_context.count(chr(10)) + 1} items)')

        filtered = filter_out(source_posts, ["RT", "https://", "@"])
        random.shuffle(filtered)

        previous_posts = "\n".join([f"- {post}" for post in filtered[:30]])

        time_context = now_et.strftime("%A, %B %d, %Y at %I:%M %p ET")

        activity_section = ""
        if activity_context:
            activity_section = (
                f"For background context only — here's what Michael has been up to lately:\n\n"
                f"{activity_context}\n\n"
                "This is just context. Most of the time, DON'T reference it directly. "
                "Only occasionally (maybe 1 in 4 posts) should you draw from it, and when "
                "you do, be subtle — a passing thought, not a review or summary. "
                "The majority of posts should be original observations, opinions, or vibes "
                "that have nothing to do with the activity feed.\n\n"
            )

        prompt = (
            f"Current date and time: {time_context}\n\n"
            f"{activity_section}"
            f"Here are some of Michael's actual recent posts for voice reference:\n\n"
            f"{previous_posts}\n\n"
            "Write one new post in this exact voice. Be aware of the current date/time "
            "and recent activity — it can inform the post naturally but don't force it. "
            "Many posts have nothing to do with current events or activity.\n\n"
            "Just the post text, nothing else. No quotes around it."
        )

        generated = generate(SYSTEM_PROMPT, prompt, max_tokens=120)

        # Strip quotes if the model wraps the output
        if generated.startswith('"') and generated.endswith('"'):
            generated = generated[1:-1]

        print(f'Generated: {generated}')

        if generated is not None and len(generated) < 480:
            if not DEBUG:
                if generated != '':
                    mastodon.status_post(status=generated)
                    print(f'Posted: {generated}')
                else:
                    print('No status to post.')
            else:
                print(f'Didn\'t post \'{generated}\' because DEBUG is True.')

        elif generated is None:
            print('Post is empty, sorry.')
        else:
            print(f'BAD POST (too long): {generated}')

    else:
        if DEBUG:
            print(f'{guess} No, sorry, not this time.')

    if reply_guess == 0 and awake:
        source_mentions = mastodon.notifications(types=["mention"], limit=1)

        print('\nGetting last mention.')

        for mention in source_mentions:
            f = HTMLFilter()
            f.feed(mention.status.content)

            mention_text = re.sub(r'(@)\S+', '', f.text).strip()

            # Only do this while awake, sometimes.
            if random.choice(range(FAVE_ODDS)) == 0 and awake:
                if not mention.status.favourited:
                    mastodon.status_favourite(id=mention.status.id)
                    print(f'\nFavorited: {mention.status.content}')

            # Build thread context
            thread_parts = [mention_text]
            if mention.status.in_reply_to_id is not None:
                parent = mention.status
                while parent.in_reply_to_id is not None:
                    parent = mastodon.status(id=parent.in_reply_to_id)
                    f = HTMLFilter()
                    f.feed(parent.content)
                    parent_text = re.sub(r'(@)\S+', '', f.text).strip()
                    thread_parts.insert(0, parent_text)

            # Check if we already replied
            replied = False
            bot_statuses = mastodon.account_statuses(id=BOT_ID, limit=50)
            for s in bot_statuses:
                if s.in_reply_to_id == mention.status.id:
                    replied = True
                    print('Already replied to this mention.')
                    break

            if awake and not replied:
                print('Generating reply...\n')

                if not DEBUG:
                    filtered = filter_out(source_posts, ["RT", "https://", "@"])
                    random.shuffle(filtered)
                    previous_posts = "\n".join([f"- {post}" for post in filtered[:20]])

                    reply_system = (
                        SYSTEM_PROMPT + "\n\n"
                        f"Here are some of Michael's recent posts for voice reference:\n\n"
                        f"{previous_posts}\n\n"
                        "You are replying to someone. Keep it short, casual, lowercase. "
                        "Often just a few words. Think 'heck yeah' or 'oh nice' or a quick genuine reaction."
                    )

                    thread_display = "\n".join([f"> {part}" for part in thread_parts])
                    time_context = now_et.strftime("%A, %B %d, %Y at %I:%M %p ET")
                    reply_prompt = (
                        f"Current date and time: {time_context}\n\n"
                        f"Thread:\n{thread_display}\n\n"
                        "Write a short reply in Michael's voice. Just the reply text, nothing else."
                    )

                    generated_reply = generate(reply_system, reply_prompt, max_tokens=80)

                    # Strip quotes
                    if generated_reply.startswith('"') and generated_reply.endswith('"'):
                        generated_reply = generated_reply[1:-1]
                else:
                    generated_reply = 'test reply from debug mode'

                print(f'Reply: {generated_reply}')

                if generated_reply and len(generated_reply) < 240:
                    if not DEBUG:
                        mastodon.status_post(status=generated_reply, in_reply_to_id=mention.status.id)
                        print(f'Replied: {generated_reply}')
                    else:
                        print(f'Didn\'t reply \'{generated_reply}\' because DEBUG is True.')
            else:
                print('Not replying this time.')
    else:
        if DEBUG:
            print(f'{reply_guess} No reply this time.')

    # Occasionally boost a recent @mknepprath post
    if awake and random.choice(range(BOOST_ODDS)) == 0:
        print('\nChecking for posts to boost...')
        try:
            recent = mastodon.account_statuses(id=SOURCE_ID, limit=5, exclude_replies=True)
            # Find a post we haven't already boosted
            for post in recent:
                if not post.reblogged and not post.in_reply_to_id:
                    mastodon.status_reblog(id=post.id)
                    f = HTMLFilter()
                    f.feed(post.content)
                    print(f'Boosted: {f.text[:80]}')
                    break
            else:
                print('No new posts to boost.')
        except Exception as e:
            print(f'Error boosting: {e}')


if __name__ == '__main__':
    main()
