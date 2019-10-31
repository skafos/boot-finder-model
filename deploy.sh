#!/usr/bin/env bash
set -e

$(awscli ecr get-login --no-include-email --region us-east-1)

echo "Grabbing the latest image..."
IMAGE_TAG=$(awscli ecr list-images --repository-name bootfinder | jq -r '.imageIds | map (.imageTag)|sort|.[]' | sort -r | head -1)

echo "Deploying CloudFormation..."
awscli cloudformation deploy \
--template-file cloudformation.yml \
--stack-name bootfinder \
--capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
--parameter-overrides \
  ImageURL=445227032534.dkr.ecr.us-east-1.amazonaws.com/bootfinder:$IMAGE_TAG
