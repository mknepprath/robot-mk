# @robot_mk

A Mastodon bot that mimics Michael Knepprath's writing style using Claude AI.

## Features

- **Authentic voice mimicry**: Uses Claude API with enhanced prompt engineering to capture Michael's unique writing style
- **Coffee post filtering**: Intelligently reduces excessive coffee-related posts while maintaining natural variety
- **Smart reply system**: Contextual replies that maintain conversation flow
- **Modern dependencies**: Updated to use latest versions of key libraries

## Setup

1. **Clone the repository**
   ```bash
   git clone [repo-url]
   cd robot-mk
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   export ANTHROPIC_API_KEY="your-claude-api-key"
   export MASTODON_CLIENT_KEY="your-mastodon-client-key"
   export MASTODON_CLIENT_SECRET="your-mastodon-client-secret"
   export MASTODON_ACCESS_TOKEN="your-mastodon-access-token"
   ```

4. **Test locally**
   ```bash
   python ebooks.py
   ```

## Deployment

### AWS Lambda

1. Make sure you have AWS CLI installed and configured.
2. Update the deployment script if needed for the new dependencies.
3. Run the deployment:
   ```bash
   sh deploy.sh
   ```

**Note**: The deployment bundle now includes the `anthropic` library instead of `openai`. You may still need to add `pandas` as a Lambda layer using the ARN from [Klayers](https://github.com/keithrozario/Klayers/tree/master/deployments/python3.9).

## Key Improvements

### Switch to Claude API
- Replaced OpenAI GPT-4 with Claude 3.5 Sonnet for better quality and more authentic voice matching
- Enhanced system prompts that specifically capture Michael's writing characteristics
- Better handling of conversational context in replies

### Coffee Post Management  
- Intelligent filtering of training data to reduce coffee-heavy examples
- Runtime filtering of generated posts to prevent coffee obsession
- Maintains natural variety while avoiding repetitive topics

### Enhanced Prompt Engineering
- Detailed character description focusing on Michael's interests: tech, design, creativity
- Examples of his writing style characteristics: thoughtful, conversational, informative
- Better context awareness including current date and authentic voice patterns

### Updated Dependencies
- `anthropic>=0.40.0` - Modern Claude API client
- `Mastodon.py>=1.8.1` - Latest Mastodon library  
- `pandas>=2.2.0` - Updated data processing
- `requests>=2.32.0` - Secure HTTP handling

## Configuration

Edit `local_settings.py` to adjust:
- `ODDS`: How often the bot posts (higher = less frequent)
- `REPLY_ODDS`: How often it replies to mentions  
- `DEBUG`: Set to `True` for testing without posting

## How It Works

1. **Data Collection**: Fetches recent posts from Michael's Mastodon account
2. **Content Filtering**: Removes excessive coffee content and inappropriate material
3. **Style Analysis**: Uses Claude to analyze and replicate Michael's authentic voice
4. **Generation**: Creates new posts that sound naturally like Michael would write them
5. **Quality Control**: Additional filtering to ensure authenticity and appropriateness

The bot sleeps during typical sleeping hours (3 AM - 11 AM) to maintain realistic posting patterns.