#!/usr/bin/env bash
# WARDEN — one-command "this is really on AWS" proof for judges.
# Read-only. Prints identity, the deployed stack, the KMS keys, the data plane,
# and hits the live API. Region + creds come from your configured AWS CLI.
set -uo pipefail
REGION="${AWS_REGION:-ap-south-1}"
STACK="WardenStack"
line() { printf '\n\033[38;5;66m%s\033[0m\n' "── $1 ──────────────────────────────────────────"; }

line "1 · Identity — whose account is this?"
aws sts get-caller-identity --query '{account:Account, user:Arn}' --output table

line "2 · The deployed stack (Infrastructure-as-Code)"
aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].{Stack:StackName, Status:StackStatus, Created:CreationTime}" --output table
echo "   resources provisioned:"
aws cloudformation list-stack-resources --stack-name "$STACK" --region "$REGION" \
  --query "length(StackResourceSummaries)" --output text | sed 's/^/     /'

line "3 · Stack outputs (live endpoints)"
aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table

line "4 · The moat — two KMS asymmetric keys"
aws kms list-aliases --region "$REGION" \
  --query "Aliases[?starts_with(AliasName,'alias/warden')].[AliasName,TargetKeyId]" --output table

line "5 · Data plane — DynamoDB table + the service Lambdas"
aws dynamodb describe-table --table-name warden --region "$REGION" \
  --query "Table.{Table:TableName, Status:TableStatus, Items:ItemCount}" --output table
aws lambda list-functions --region "$REGION" \
  --query "Functions[?starts_with(FunctionName,'WardenStack')].FunctionName" --output table

line "6 · The orchestrator — Step Functions saga"
aws stepfunctions list-state-machines --region "$REGION" \
  --query "stateMachines[?contains(name,'WardenSaga')].[name,stateMachineArn]" --output table

line "7 · Live HTTPS request to the deployed API"
API=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
echo "   GET ${API}cases"
curl -s -o /dev/null -w "   -> HTTP %{http_code} from %{remote_ip} (execute-api.$REGION.amazonaws.com)\n" "${API}cases"

printf '\n\033[38;5;79m✓ Every resource above lives in AWS account %s, region %s.\033[0m\n' \
  "$(aws sts get-caller-identity --query Account --output text)" "$REGION"
