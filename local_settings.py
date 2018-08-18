'''
Local Settings for robot_mk.
'''

SOURCE_ACCOUNTS = ['mknepprath'] #A list of comma-separated, quote-enclosed Twitter handles of account that you'll generate tweets based on. It should look like ["account1", "account2"]. If you want just one account, no comma needed.
ODDS = 2 #How often do you want this to run? 1/8 times?
FAVE_ODDS = 2
REPLY_ODDS = 2
QUOTE_ODDS = 2
ORDER = 2 #how closely do you want this to hew to sensical? 1 is low and 3 is high.
DEBUG = False #Set this to False to start Tweeting live
TWEET_ACCOUNT = 'robot_mk'

#heroku run worker --app robot-mk
