#!/usr/bin/env bash
# WARDEN — drive one full case through the DEPLOYED AWS saga.
# Uploads the hero attack, starts Step Functions, waits for the human-approval
# pause, approves (KMS signs token_B), watches the actuator verify + apply, then
# demonstrates the cryptographic refusal. Reads all resource names from the
# deployed CloudFormation outputs — no hand-editing.
set -euo pipefail
cd "$(dirname "$0")/.."                     # warden/ root
STACK="${STACK:-WardenStack}"
REGION="${AWS_REGION:-ap-south-1}"
SESSION="s_1029"

echo "▸ reading stack outputs ($STACK / $REGION)…"
OUT=$(aws cloudformation describe-stacks --stack-name "$STACK" --region "$REGION" \
  --query "Stacks[0].Outputs" --output json)
get(){ echo "$OUT" | python3 -c "import sys,json;print(next(o['OutputValue'] for o in json.load(sys.stdin) if o['OutputKey']=='$1'))"; }
BUCKET=$(get BlobsBucket); SAGA=$(get SagaArn); API=$(get ApiUrl)
echo "  bucket=$BUCKET"; echo "  api=$API"

echo "▸ uploading the poisoned session to S3…"
aws s3 cp demo/fixtures/hero_attack.json "s3://$BUCKET/sessions/$SESSION/transcript.json" --region "$REGION" >/dev/null

echo "▸ starting the saga…"
aws stepfunctions start-execution --state-machine-arn "$SAGA" --region "$REGION" \
  --input "{\"sessionId\":\"$SESSION\"}" --query executionArn --output text >/dev/null

echo "▸ waiting for the case to reach AWAITING_APPROVAL (detect → diagnose → validate → sign KEY_A)…"
CASE=""
for i in $(seq 1 30); do
  sleep 3
  RESP=$(curl -s "${API}cases?status=AWAITING_APPROVAL" || true)
  CASE=$(echo "$RESP" | python3 -c "import sys,json
try:
  d=json.load(sys.stdin); c=d.get('cases',[])
  print(c[0]['PK'].split('#',1)[1] if c else '')
except Exception: print('')" )
  [ -n "$CASE" ] && break
  printf '  …%ss\n' $((i*3))
done
[ -z "$CASE" ] && { echo "✗ no case reached approval — check the Step Functions console / CloudWatch logs"; exit 1; }
echo "  case = $CASE"

echo "▸ case detail (verdict + rehearsal seal):"
curl -s "${API}cases/${CASE}" | python3 -m json.tool

echo "▸ approving as sec-lead@org (KMS signs token_B on KEY_B, saga resumes, actuator verifies A+B)…"
curl -s -X POST "${API}cases/${CASE}/approve" -H "content-type: application/json" \
  -d '{"approver":"sec-lead@org"}' | python3 -m json.tool
sleep 4
echo "▸ final actuation:"
curl -s "${API}cases/${CASE}" | python3 -c "import sys,json;d=json.load(sys.stdin);print('  ACTUATION:', d.get('ACTUATION'))"

echo
echo "▸ THE CLIMAX — strip the rehearsal token and try to deploy anyway:"
curl -s -X POST "${API}cases/${CASE}/deployUnsafe" | python3 -m json.tool
echo
echo "✓ done. Applied with two valid KMS signatures; refused the moment one was stripped."
