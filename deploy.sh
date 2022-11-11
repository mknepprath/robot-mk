#!/bin/bash

# Bundle the dependencies
pip install -t bundle -r requirements.txt --upgrade

# Add function code to bundle
cp ebooks.py bundle
cp lambda_function.py bundle
cp local_settings.py bundle

# Delete dependencies hosted on AWS
rm -rf bundle/numpy bundle/pandas bundle/numpy-*.dist-info bundle/pandas-*.dist-info

# Zip the bundle
cd bundle
zip -r ../bundle.zip *
cd ..

# Upload the bundle to S3
aws s3 cp bundle.zip s3://robotmk

# Delete the bundle locally
rm -rf bundle bundle.zip

# Update the Lambda function
aws lambda update-function-code --function-name robotMk --s3-bucket robotmk --s3-key bundle.zip --region us-east-1
