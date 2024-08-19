#!/bin/bash

# Exit script on any error
set -e

# Create and clear the bundle directory to avoid leftovers
rm -rf bundle
mkdir -p bundle

# Bundle the dependencies for the correct platform architecture
pip install --target bundle -r requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: --upgrade

# Add function code to bundle in one step
cp {ebooks.py,lambda_function.py,local_settings.py} bundle/

# Remove unnecessary files to minimize bundle size
find bundle -type d -name 'numpy*' | xargs rm -rf

# Zip the bundle
(cd bundle && zip -r ../bundle.zip .)

# Upload the bundle to S3 and update the Lambda function in one step
aws s3 cp bundle.zip s3://robotmk && \
aws lambda update-function-code --function-name robotMk --s3-bucket robotmk --s3-key bundle.zip --region us-east-1

# Clean up local files
rm -rf bundle bundle.zip