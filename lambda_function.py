import json

import ebooks


def lambda_handler(event, context):

    ebooks.main()

    return {
        'statusCode': 200,
        'body': json.dumps('Ran ebooks.py!')
    }
