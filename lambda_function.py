import json
import ebooks


def lambda_handler(event, context):
    """
    AWS Lambda handler for the robot_mk Mastodon bot.
    Now using Claude API instead of OpenAI for better authenticity.
    """
    try:
        ebooks.main()
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully executed robot_mk bot with Claude API!')
        }
    except Exception as e:
        print(f"Error in lambda execution: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
