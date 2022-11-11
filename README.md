# @robot_mk

Based on Horse_ebooks.

To run:

1. Pull down the repo.
1. Get some tokens from Twitter and set them up as environment variables.
1. Run `python ebooks.py`.

To deploy:

1. Make sure you have AWS CLI installed and configured.
2. Run `sh deploy.sh`.

This will automatically bundle up the function and dependencies and deploy it to AWS Lambda.

Note that `numpy` and `pandas` are not included in the deployment bundle. They must
be added as layers to the Lambda function. Add them using the ARN here: [Layers for Python 3.9](https://github.com/keithrozario/Klayers/tree/master/deployments/python3.9).
