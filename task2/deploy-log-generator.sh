#!/bin/bash
# CloudFormationデプロイスクリプト（Linux/Mac用）

set -e

STACK_NAME="${STACK_NAME:-hands-on-log-generator}"
REGION="${AWS_REGION:-ap-northeast-1}"
ACTION="${1:-deploy}"

case "$ACTION" in
  deploy)
    echo "Deploying CloudFormation stack: ${STACK_NAME}"
    aws cloudformation deploy \
      --template-file setup-log-generator.yaml \
      --stack-name "${STACK_NAME}" \
      --capabilities CAPABILITY_NAMED_IAM \
      --region "${REGION}" \
      --tags Project=HandsOn Component=LogGenerator

    echo ""
    echo "Stack deployed successfully!"
    echo ""
    echo "Outputs:"
    aws cloudformation describe-stacks \
      --stack-name "${STACK_NAME}" \
      --region "${REGION}" \
      --query 'Stacks[0].Outputs' \
      --output table
    ;;

  destroy)
    echo "Deleting CloudFormation stack: ${STACK_NAME}"
    aws cloudformation delete-stack \
      --stack-name "${STACK_NAME}" \
      --region "${REGION}"

    echo "Waiting for stack deletion..."
    aws cloudformation wait stack-delete-complete \
      --stack-name "${STACK_NAME}" \
      --region "${REGION}"

    echo "Stack deleted successfully!"
    ;;

  status)
    echo "Checking stack status: ${STACK_NAME}"
    aws cloudformation describe-stacks \
      --stack-name "${STACK_NAME}" \
      --region "${REGION}" \
      --query 'Stacks[0].[StackName,StackStatus]' \
      --output table
    ;;

  *)
    echo "Usage: $0 [deploy|destroy|status]"
    echo ""
    echo "Commands:"
    echo "  deploy  - Deploy or update the stack (default)"
    echo "  destroy - Delete the stack"
    echo "  status  - Check stack status"
    exit 1
    ;;
esac

