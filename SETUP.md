# Setup Guide for @robot_mk

This guide will help you set up the robot_mk Mastodon bot with the new Claude API integration.

## Prerequisites

- Python 3.8+ installed
- Access to Anthropic Claude API
- Mastodon account and app credentials

## Step 1: Get Claude API Key

1. Sign up at [Anthropic Console](https://console.anthropic.com/)
2. Create a new API key
3. Copy the key (starts with `sk-ant-api03-...`)

## Step 2: Get Mastodon Credentials

1. Go to your Mastodon instance (e.g., mastodon.social)
2. Go to Preferences → Development
3. Click "New Application"
4. Fill in the details:
   - **Application name**: `robot_mk` (or your preferred name)
   - **Scopes**: Select `read`, `write`, and `follow`
5. Save the application
6. Copy the following values:
   - Client key
   - Client secret 
   - Your access token

## Step 3: Set Environment Variables

Create a `.env` file in the robot-mk directory:

```bash
# Claude API
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"

# Mastodon API
export MASTODON_CLIENT_KEY="your-client-key-here"
export MASTODON_CLIENT_SECRET="your-client-secret-here" 
export MASTODON_ACCESS_TOKEN="your-access-token-here"
```

Then load the environment variables:
```bash
source .env
```

## Step 4: Install Dependencies

```bash
cd robot-mk
pip install -r requirements.txt
```

## Step 5: Test the Setup

Run the test script to verify everything is working:

```bash
python test_bot.py
```

This will test:
- ✅ Environment variables are set correctly
- ✅ All Python packages are installed
- ✅ Coffee filtering logic works
- ✅ Bot can run in DEBUG mode

## Step 6: Configure the Bot

Edit `local_settings.py` to customize:

- `SOURCE_ID`: Your Mastodon user ID (find this in your profile URL)
- `ODDS`: How often the bot posts (higher = less frequent)
- `DEBUG`: Set to `True` for testing, `False` for live posting

## Step 7: Run Locally

Test with DEBUG mode first:

```bash
# Edit local_settings.py to set DEBUG = True
python ebooks.py
```

When you're satisfied, set `DEBUG = False` and run:

```bash
python ebooks.py
```

## Step 8: Deploy to AWS Lambda (Optional)

1. Configure AWS CLI with your credentials
2. Make sure you have an S3 bucket named `robotmk`
3. Run the deployment script:

```bash
./deploy.sh
```

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
- Make sure you've sourced your `.env` file: `source .env`
- Check that the key starts with `sk-ant-api03-`

### "ModuleNotFoundError: No module named 'anthropic'"
- Install dependencies: `pip install -r requirements.txt`
- If using virtual environment, make sure it's activated

### "HTTP 401 Unauthorized" from Mastodon
- Verify your Mastodon credentials are correct
- Make sure your app has the right scopes (read, write, follow)

### Bot posts too much coffee content
- The improved coffee filtering should handle this automatically
- If needed, adjust the `COFFEE_TERMS` list in `ebooks.py`
- Lower the `max_coffee_ratio` in `filter_coffee_heavy_posts()`

## Key Improvements

- 🤖 **Better AI**: Switched from GPT-4 to Claude 3.5 Sonnet for more authentic voice
- ☕ **Coffee Control**: Intelligent filtering reduces excessive coffee posting  
- 🎯 **Enhanced Prompts**: Detailed system prompts capture Michael's unique writing style
- 🔄 **Modern Dependencies**: Updated to latest stable versions
- 🧪 **Better Testing**: Comprehensive test script for easy verification

## Support

If you run into issues:

1. Run `python test_bot.py` to diagnose problems
2. Check the console output for specific error messages
3. Verify your environment variables are set correctly
4. Make sure all dependencies are installed with the right versions