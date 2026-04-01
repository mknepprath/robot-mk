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

STRUCTURAL RULES — these are critical:
- NO punchlines. NO setups. NO "X? more like Y" constructions.
- NO internet slang he doesn't use: "go off", "I said what I said", "and I took that personally", "it's giving", "no cap", "rent free", "understood the assignment"
- NO constructed jokes. The humor is accidental, not engineered.
- Posts should feel like something muttered, not performed.
- If it sounds like a tweet that's trying to go viral, delete it and start over.

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
- sure am getting a lot more twitter spam starting about a week ago
- .grid { display: flex; ... } 😑
- love this movie sooo much

BAD examples (DO NOT write like this):
- "spent the morning wrestling with a stubborn line of code"
- "discovered a new coffee shop today"
- "been pondering the existential crisis of my houseplants"
- anything with a setup-punchline story structure
- "budget constraints? more like budget genius" (this is a constructed joke)
- "but go off i guess" (internet slang he doesn't use)
- anything that builds to a clever turn or reversal"""


ACTIVITY_URL = "https://mknepprath.com/api/v1/activity?max_results=30&min_rating=0"

# Load voice samples from Twitter archive
VOICE_SAMPLES = []
try:
    voice_path = os.path.join(os.path.dirname(__file__), 'voice_samples.json')
    with open(voice_path, 'r') as f:
        VOICE_SAMPLES = json.load(f)
    print(f'Loaded {len(VOICE_SAMPLES)} voice samples')
except Exception:
    print('No voice samples found')


def fetch_activity_feed():
    """Fetch recent activity from mknepprath.com and format as context."""
    try:
        with urlopen(ACTIVITY_URL) as response:
            data = json.loads(response.read().decode())

        # Skip toots/skeets (already in Mastodon posts), repos (noisy), and robot posts (that's us)
        skip_types = {"TOOT", "SKEET", "REPO", "ROBOT"}
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


def get_bot_recent_posts(mastodon, limit=15):
    """Fetch robot_mk's own recent posts for conversational memory."""
    try:
        statuses = mastodon.account_statuses(id=BOT_ID, limit=limit, exclude_replies=True)
        posts = []
        for s in statuses:
            if s.reblog:
                continue
            f = HTMLFilter()
            f.feed(s.content)
            text = f.text.strip()
            if text:
                posts.append(text)
        return posts
    except Exception as e:
        print(f"Error fetching bot's own posts: {e}")
        return []


def system_with_voice(extra="", num_samples=25, bot_memory=None):
    """Build a system prompt with random voice samples and conversational memory."""
    voice = ""
    if VOICE_SAMPLES:
        samples = random.sample(VOICE_SAMPLES, min(num_samples, len(VOICE_SAMPLES)))
        voice = (
            "\n\nREAL POSTS by Michael from his archive — this is his actual voice:\n"
            + "\n".join([f"- {s}" for s in samples])
        )

    memory = ""
    if bot_memory:
        memory = (
            "\n\nYOUR OWN RECENT POSTS — this is what you've been saying lately. "
            "Use this to maintain continuity. Don't repeat yourself. You can follow up "
            "on previous thoughts, reference things you've already mentioned, or let "
            "running threads develop naturally. But never copy or rephrase a recent post:\n"
            + "\n".join([f"- {p}" for p in bot_memory])
        )

    return SYSTEM_PROMPT + voice + memory + ("\n\n" + extra if extra else "")


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

    is_april_fools = now_et.month == 4 and now_et.day == 1

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
    bot_memory = []

    if awake:
        print('Fetching my own recent posts for memory...')
        bot_memory = get_bot_recent_posts(mastodon)
        print(f'Memory: {len(bot_memory)} recent posts')

    # Daily post cap — count posts made today
    posts_today = 0
    if awake:
        try:
            today_start = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
            my_statuses = mastodon.account_statuses(id=BOT_ID, limit=20)
            for s in my_statuses:
                if s.created_at.replace(tzinfo=None) >= today_start.replace(tzinfo=None):
                    posts_today += 1
            print(f'Posts today: {posts_today}/{MAX_POSTS_PER_DAY}')
            if posts_today >= MAX_POSTS_PER_DAY:
                print('Hit daily post cap. Skipping all posting.')
                return
        except Exception as e:
            print(f'Error checking daily cap: {e}')

    # Guarantee at least one post on April Fools
    if is_april_fools and posts_today == 0 and awake:
        guess = 0

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

        # Recent Mastodon posts (for recency context, not voice)
        filtered = filter_out(source_posts, ["RT", "https://", "@"])
        random.shuffle(filtered)
        recent_section = "\n".join([f"- {post}" for post in filtered[:10]])

        time_context = now_et.strftime("%A, %B %d, %Y at %I:%M %p ET")

        activity_section = ""
        if activity_context and (random.choice(range(4)) == 0 or is_april_fools):
            activity_section = (
                f"Michael has been up to this stuff lately (background only):\n\n"
                f"{activity_context}\n\n"
                "You MAY reference one of these things in passing, but keep it subtle. "
                "A passing thought, not a review.\n\n"
            )

        if is_april_fools:
            prompt = (
                f"Current date and time: {time_context}\n\n"
                f"{activity_section}"
                f"Here are some of his recent Mastodon posts for context:\n\n"
                f"{recent_section}\n\n"
                "It's April Fools' Day. Write a post that is a prank — something deadpan "
                "and believable that sounds like a real announcement or life update, but is "
                "actually absurd or fake. It should fool people for a few seconds before they "
                "realize it's a joke. Stay in Michael's voice — lowercase, terse, dry. "
                "Reference his real projects, interests, or recent activity to make it convincing. "
                "Do NOT say 'april fools' or hint that it's a joke. Let people figure it out.\n\n"
                "Just the post text, nothing else. No quotes around it."
            )
        else:
            prompt = (
                f"Current date and time: {time_context}\n\n"
                f"{activity_section}"
                f"Here are some of his recent Mastodon posts for context on what he's been talking about lately:\n\n"
                f"{recent_section}\n\n"
                "Write one new post in this exact voice. Match the tone, length, and style of "
                "the archive posts in the system prompt. Be aware of the current date/time and "
                "recent activity but don't force it. Many posts have nothing to do with current events.\n\n"
                "Just the post text, nothing else. No quotes around it."
            )

        generated = generate(system_with_voice(bot_memory=bot_memory), prompt, max_tokens=120)

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

                    reply_system = system_with_voice(
                        "You are replying to someone. Keep it short, casual, lowercase. "
                        "Often just a few words. Think 'heck yeah' or 'oh nice' or a quick genuine reaction.",
                        bot_memory=bot_memory,
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

    # Occasionally share a post from one of Michael's bot accounts with commentary
    SIBLING_BOTS = {
        "109447224294183229": {
            "handle": "@EveryPkmnCard",
            "context": "Posts a new Pokemon card every hour. Michael built this bot.",
        },
        "109852410462840995": {
            "handle": "@PokemonFacts",
            "context": "Posts Pokemon facts. Another one of Michael's bots.",
        },
        "113479454947259743": {
            "handle": "@boutbot",
            "context": "Bot for Who Goes There?, a social deduction game Michael built.",
        },
        "113479368818279476": {
            "handle": "@familiarlilt",
            "context": "Bot for Lilt, a text adventure game Michael built.",
        },
        "113490843400044713": {
            "handle": "@designprompts",
            "context": "Posts design prompts and challenges. Another Michael creation.",
        },
    }

    if awake and random.choice(range(BOOST_ODDS)) == 0:
        print('\nChecking sibling bots for commentary boost...')
        try:
            bot_id = random.choice(list(SIBLING_BOTS.keys()))
            bot_info = SIBLING_BOTS[bot_id]
            recent = mastodon.account_statuses(id=bot_id, limit=5, exclude_replies=True)

            # Check our recent posts to avoid commenting on the same thing twice
            my_recent = mastodon.account_statuses(id=BOT_ID, limit=30)
            recent_urls = set()
            for s in my_recent:
                f = HTMLFilter()
                f.feed(s.content)
                recent_urls.add(f.text)

            for post in recent:
                if post.url and not any(post.url in u for u in recent_urls):
                    f = HTMLFilter()
                    f.feed(post.content)
                    post_text = f.text.strip()

                    if not post_text:
                        continue

                    commentary_system = system_with_voice(
                        f"You are commenting on a post from {bot_info['handle']}. "
                        f"{bot_info['context']} You made this bot — it's your project. "
                        "React naturally, the way you'd react to your own bot doing its thing. "
                        "Maybe you think the output is funny, or mid, or you have a take on the content. "
                        "Be honest. Keep it short. The post URL will be appended automatically.",
                        bot_memory=bot_memory,
                    )

                    commentary_prompt = (
                        f"Here's the post from {bot_info['handle']}:\n\n"
                        f"{post_text[:300]}\n\n"
                        "Write a short comment. Just the text, nothing else."
                    )

                    commentary = generate(commentary_system, commentary_prompt, max_tokens=80)

                    if commentary.startswith('"') and commentary.endswith('"'):
                        commentary = commentary[1:-1]

                    status = f"{commentary}\n\n{post.url}"

                    if len(status) < 480:
                        if not DEBUG:
                            mastodon.status_post(status=status)
                            print(f'Commentary on {bot_info["handle"]}: {commentary}')
                        else:
                            print(f'Would comment on {bot_info["handle"]}: {commentary}')
                    break
            else:
                print(f'No new posts from {bot_info["handle"]} to comment on.')
        except Exception as e:
            print(f'Error with sibling bot commentary: {e}')

    # Occasionally reply to @mknepprath's own posts
    if awake and random.choice(range(36)) == 0:
        print('\nChecking if I should reply to @mknepprath...')
        try:
            recent = mastodon.account_statuses(id=SOURCE_ID, limit=5, exclude_replies=True)
            bot_statuses = mastodon.account_statuses(id=BOT_ID, limit=50)
            replied_to_ids = {s.in_reply_to_id for s in bot_statuses if s.in_reply_to_id}

            for post in recent:
                if post.id not in replied_to_ids and not post.in_reply_to_id:
                    f = HTMLFilter()
                    f.feed(post.content)
                    post_text = f.text.strip()
                    if not post_text:
                        continue

                    reply_system = system_with_voice(
                        "You are replying to a post by the real @mknepprath — the person you're "
                        "a doppelganger of. This is your chance to riff on what he said. "
                        "Be playful, deadpan, or just react. You're basically his echo with opinions. "
                        "Keep it very short.",
                        bot_memory=bot_memory,
                    )

                    reply_prompt = (
                        f"Here's what @mknepprath posted:\n\n"
                        f"{post_text[:300]}\n\n"
                        "Write a short reply. Just the text, nothing else."
                    )

                    reply = generate(reply_system, reply_prompt, max_tokens=80)
                    if reply.startswith('"') and reply.endswith('"'):
                        reply = reply[1:-1]

                    if reply and len(reply) < 240:
                        if not DEBUG:
                            mastodon.status_post(status=reply, in_reply_to_id=post.id)
                            print(f'Replied to @mknepprath: {reply}')
                        else:
                            print(f'Would reply to @mknepprath: {reply}')
                    break
        except Exception as e:
            print(f'Error replying to @mknepprath: {e}')

    # Follow-back management: follow anyone who follows us, unfollow anyone who unfollowed
    if awake and random.choice(range(6)) == 0:
        print('\nManaging follows...')
        try:
            followers = mastodon.account_followers(id=BOT_ID, limit=80)
            following = mastodon.account_following(id=BOT_ID, limit=80)

            follower_ids = {f.id for f in followers}
            following_ids = {f.id for f in following}

            # Follow back new followers
            for follower in followers:
                if follower.id not in following_ids and not follower.bot:
                    mastodon.account_follow(id=follower.id)
                    print(f'Followed back: @{follower.acct}')

            # Unfollow anyone who unfollowed us (except the source account)
            for account in following:
                if account.id not in follower_ids and str(account.id) != SOURCE_ID:
                    mastodon.account_unfollow(id=account.id)
                    print(f'Unfollowed: @{account.acct}')
        except Exception as e:
            print(f'Error managing follows: {e}')

    # Rarely reply to a follower's recent post (they followed us = consent)
    if awake and random.choice(range(48)) == 0:
        print('\nChecking followers timeline for something to reply to...')
        try:
            following = mastodon.account_following(id=BOT_ID, limit=80)
            # Skip the source account and other bots
            real_follows = [f for f in following if str(f.id) != SOURCE_ID
                           and str(f.id) != BOT_ID and not f.bot]

            if real_follows:
                target = random.choice(real_follows)
                their_posts = mastodon.account_statuses(id=target.id, limit=5, exclude_replies=True)

                bot_statuses = mastodon.account_statuses(id=BOT_ID, limit=50)
                replied_to_ids = {s.in_reply_to_id for s in bot_statuses if s.in_reply_to_id}

                for post in their_posts:
                    if post.id not in replied_to_ids and not post.in_reply_to_id:
                        f = HTMLFilter()
                        f.feed(post.content)
                        post_text = f.text.strip()
                        if not post_text or len(post_text) < 10:
                            continue

                        reply_system = system_with_voice(
                            f"You are replying to a post by @{target.acct}, someone who follows you. "
                            "Be casual and friendly. Just a quick genuine reaction. Keep it very short.",
                            bot_memory=bot_memory,
                        )

                        reply_prompt = (
                            f"Here's what @{target.acct} posted:\n\n"
                            f"{post_text[:300]}\n\n"
                            "Write a short reply. Just the text, nothing else."
                        )

                        reply = generate(reply_system, reply_prompt, max_tokens=60)
                        if reply.startswith('"') and reply.endswith('"'):
                            reply = reply[1:-1]

                        if reply and len(reply) < 200:
                            if not DEBUG:
                                mastodon.status_post(status=reply, in_reply_to_id=post.id)
                                print(f'Replied to @{target.acct}: {reply}')
                            else:
                                print(f'Would reply to @{target.acct}: {reply}')
                        break
        except Exception as e:
            print(f'Error replying to follower: {e}')

    # Rarely review own post history
    if awake and random.choice(range(72)) == 0:
        print('\nReviewing my own post history...')
        try:
            my_posts = mastodon.account_statuses(id=BOT_ID, limit=20, exclude_replies=True)
            # Pick a post from a few days ago
            older_posts = [p for p in my_posts[5:] if not p.reblog]

            if older_posts:
                target_post = random.choice(older_posts)
                f = HTMLFilter()
                f.feed(target_post.content)
                old_text = f.text.strip()

                if old_text:
                    review_system = system_with_voice(
                        "You are looking back at one of your own previous posts and reacting to it. "
                        "Be honest — was it good? cringe? funny? did it age well? "
                        "This is a self-review. Be terse and real. Keep it very short.",
                        bot_memory=bot_memory,
                    )

                    review_prompt = (
                        f"Here's one of your old posts:\n\n"
                        f"{old_text[:300]}\n\n"
                        "Write a brief self-review as a reply. Just the text, nothing else."
                    )

                    review = generate(review_system, review_prompt, max_tokens=60)
                    if review.startswith('"') and review.endswith('"'):
                        review = review[1:-1]

                    if review and len(review) < 240:
                        if not DEBUG:
                            mastodon.status_post(status=review, in_reply_to_id=target_post.id)
                            print(f'Self-review of "{old_text[:40]}": {review}')
                        else:
                            print(f'Would self-review "{old_text[:40]}": {review}')
        except Exception as e:
            print(f'Error reviewing post history: {e}')

    # The count — track an arbitrary thing with no context
    if awake and random.choice(range(48)) == 0:
        print('\nChecking the count...')
        try:
            activity_context = fetch_activity_feed()
            if activity_context:
                count_system = system_with_voice(
                    "You have an obsessive habit of counting arbitrary things based on "
                    "Michael's recent activity. Pick something oddly specific to count and "
                    "post the count with zero context. Examples of the format:\n"
                    "- days since last hitchcock movie: 4\n"
                    "- consecutive runs under 6 miles: 3\n"
                    "- films watched this month: 7\n"
                    "- pokemon cards posted since last shiny: 12\n\n"
                    "Pick something real from the activity feed. Be specific and a little weird. "
                    "Just the count line, nothing else. lowercase, no punctuation at the end.",
                    bot_memory=bot_memory,
                )

                now_str = datetime.now(ET).strftime("%A, %B %d, %Y")
                count_prompt = (
                    f"Current date: {now_str}\n\n"
                    f"Recent activity:\n{activity_context}\n\n"
                    "Post one count. Just the text, nothing else."
                )

                count = generate(count_system, count_prompt, max_tokens=40)
                if count.startswith('"') and count.endswith('"'):
                    count = count[1:-1]

                if count and len(count) < 200:
                    if not DEBUG:
                        mastodon.status_post(status=count)
                        print(f'The count: {count}')
                    else:
                        print(f'Would post count: {count}')
        except Exception as e:
            print(f'Error with the count: {e}')


    # Play Lilt — occasionally send a move to @familiarlilt
    LILT_BOT_ID = "113479368818279476"
    LILT_HANDLE = "@familiarlilt"

    # Lilt is exempt from daily post cap — it's an e2e test
    if awake:
        print('\nPlaying Lilt...')
        try:
            # Check for the latest reply from @familiarlilt to us
            my_statuses = mastodon.account_statuses(id=BOT_ID, limit=30)
            lilt_statuses = mastodon.account_statuses(id=LILT_BOT_ID, limit=20)

            # Find our most recent Lilt-related post (mention of @familiarlilt)
            our_last_lilt = None
            for s in my_statuses:
                f2 = HTMLFilter()
                f2.feed(s.content)
                if LILT_HANDLE.lower() in f2.text.lower() or LILT_HANDLE.lower() in s.content.lower():
                    our_last_lilt = s
                    break

            # Find the latest reply from @familiarlilt to us
            lilt_reply = None
            for s in lilt_statuses:
                if s.in_reply_to_account_id and str(s.in_reply_to_account_id) == BOT_ID:
                    f2 = HTMLFilter()
                    f2.feed(s.content)
                    lilt_reply = f2.text.strip()
                    lilt_reply_id = s.id
                    break

            if lilt_reply:
                # We have an active game — decide next move
                print(f'Lilt said: {lilt_reply[:100]}')

                # Check if we already replied to this
                already_replied = False
                for s in my_statuses:
                    if s.in_reply_to_id == lilt_reply_id:
                        already_replied = True
                        break

                if not already_replied:
                    lilt_system = system_with_voice(
                        "You are playing Lilt, a text adventure game on Mastodon. "
                        "You play by mentioning @familiarlilt with a command. "
                        "Valid commands: go to [place], look around, look at [thing], "
                        "take [item], drop [item], use [item], open [thing], "
                        "talk to [npc], give [item] to [npc] for [item], check inventory.\n\n"
                        "You're playing as yourself — curious, exploratory, a little cautious. "
                        "Pick ONE command based on what the game just told you. "
                        "Just output the command, nothing else. No @mention, no quotes.",
                        bot_memory=bot_memory,
                    )

                    lilt_prompt = (
                        f"The game just said:\n\n{lilt_reply[:500]}\n\n"
                        "What's your next move? Just the command."
                    )

                    move = generate(lilt_system, lilt_prompt, max_tokens=40)
                    if move.startswith('"') and move.endswith('"'):
                        move = move[1:-1]
                    # Strip any @mention the model might add
                    move = re.sub(r'@\S+\s*', '', move).strip()

                    if move and len(move) < 200:
                        status = f"{LILT_HANDLE} {move}"
                        if not DEBUG:
                            mastodon.status_post(
                                status=status,
                                in_reply_to_id=lilt_reply_id,
                                visibility="unlisted",
                            )
                            print(f'Lilt move: {move}')
                        else:
                            print(f'Would play Lilt: {move}')
                else:
                    print('Already replied to last Lilt message.')

            elif not our_last_lilt:
                # No active game — start one
                status = f"{LILT_HANDLE} start"
                if not DEBUG:
                    mastodon.status_post(status=status, visibility="unlisted")
                    print('Started a new Lilt game!')
                else:
                    print('Would start a new Lilt game.')
            else:
                print('Waiting for Lilt to respond...')

        except Exception as e:
            print(f'Error playing Lilt: {e}')


if __name__ == '__main__':
    main()
