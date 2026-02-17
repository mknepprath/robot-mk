#!/bin/bash

# Exit script on any error
set -e

echo "🚀 Deploying robot_mk bot with Claude API..."

# Create and clear the bundle directory to avoid leftovers
rm -rf bundle
mkdir -p bundle

echo "📦 Installing dependencies..."
# Bundle the dependencies for the correct platform architecture
pip install --target bundle -r requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: --upgrade

echo "📁 Copying function code..."
# Add function code to bundle in one step
cp {ebooks.py,lambda_function.py,local_settings.py} bundle/

echo "🗜️  Optimizing bundle size..."
# Remove unnecessary files to minimize bundle size
# Note: Keep pandas since we still use it, but remove any test/doc directories
find bundle -type d \( -name '__pycache__' -o -name '*.dist-info' -o -name 'tests' -o -name 'docs' \) -exec rm -rf {} + 2>/dev/null || true

echo "📦 Creating deployment bundle..."
# Zip the bundle
(cd bundle && zip -r ../bundle.zip .)

BUNDLE_SIZE=$(du -h bundle.zip | cut -f1)
echo "Bundle size: $BUNDLE_SIZE"

echo "☁️  Uploading to AWS..."
# Upload the bundle to S3 and update the Lambda function in one step
aws s3 cp bundle.zip s3://robotmk && \
aws lambda update-function-code --function-name robotMk --s3-bucket robotmk --s3-key bundle.zip --region us-east-1

echo "🧹 Cleaning up..."
# Clean up local files
rm -rf bundle bundle.zip

echo "✅ Deployment complete! robot_mk is now running with Claude API."