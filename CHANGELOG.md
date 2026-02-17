# Changelog

## Version 2.0.0 - February 2026

### 🚀 Major Changes

**Switched from OpenAI to Claude API**
- Replaced `openai` library with `anthropic` library
- Updated API calls to use Claude 3.5 Sonnet model
- Improved response quality and authenticity

### ☕ Coffee Posting Improvements

**Intelligent Coffee Filtering**
- Added `contains_excessive_coffee()` function to detect coffee-heavy content
- Implemented `filter_coffee_heavy_posts()` to balance training data
- Runtime filtering prevents generated posts from being too coffee-focused
- Maintains natural variety while avoiding repetitive topics

**Configurable Thresholds**
- 30% coffee-word threshold for training data filtering
- 40% threshold for rejecting generated posts
- 15% maximum coffee posts in training examples

### 🎯 Enhanced Prompt Engineering

**Detailed Character Profile**
- Specific description of Michael's writing style and interests
- Focus on technology, design, creativity, and thoughtful observations
- Conversational tone guidelines and formatting preferences

**Better Context Awareness**
- Current date integration in system prompts
- Improved conversation threading for replies
- More natural reply generation with better context

### 📦 Dependency Updates

- `anthropic>=0.40.0` - Modern Claude API client
- `Mastodon.py>=1.8.1` - Latest Mastodon library  
- `pandas>=2.2.0` - Updated data processing
- `requests>=2.32.0` - Secure HTTP requests

### 🛠️ Development Improvements

**New Testing Framework**
- Added `test_bot.py` for comprehensive testing
- Environment variable validation
- Package import verification  
- Coffee filtering logic tests
- DEBUG mode execution tests

**Better Documentation**
- Updated README with detailed setup instructions
- New `SETUP.md` with step-by-step configuration guide
- Improved inline code documentation
- Clear troubleshooting section

**Enhanced Deployment**
- Updated `deploy.sh` with better logging and error handling
- Optimized bundle size by removing unnecessary files
- Better AWS Lambda integration

### ⚙️ Configuration Updates

**Adjusted Posting Frequency**
- `ODDS`: Increased from 108 to 144 (slightly less frequent due to higher quality)
- `IMAGE_ODDS`: Increased from 12 to 24 (disabled AI image generation temporarily)
- `REPLY_ODDS`: Increased from 6 to 8 (slightly more conservative)

### 🔧 Technical Improvements

**Error Handling**
- Better exception handling for API calls
- Graceful fallback to debug responses on API failures
- Improved logging and debugging output

**Code Quality**
- More modular functions for filtering and content generation
- Better separation of concerns
- Improved variable naming and documentation

---

## Version 1.0.0 - Original

- Basic Mastodon bot functionality
- OpenAI GPT-4 integration
- Simple prompt engineering
- AWS Lambda deployment support