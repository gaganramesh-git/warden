"""
WARDEN — infra/warden_stack.py  (AWS mode: the proof it's real)
==============================================================
One CDK stack that runs the SAME core/ logic behind thin adapters:

  DynamoDB (single table)  ·  S3 (transcripts + replay artifacts)
  2 × KMS asymmetric keys  ·  8 Lambdas  ·  Step Functions saga  ·  REST API

The security property is enforced here, in IAM, not in code:

  Sandbox-validate role  ->  kms:Sign on KEY_A only
  Approval role          ->  kms:Sign on KEY_B only
  Actuator role          ->  kms:Verify / GetPublicKey only — NO Sign, on anything
  Diagnosis role         ->  NO kms grants (it only falsifies; never signs)

So "the actuator cannot self-authorize" is a real, deployed constraint. Verify
with `cdk synth` — no AWS account needed to prove the stack + grants are valid.
"""
from __future__ import annotations

from pathlib import Path

from aws_cdk import (
    Stack, Duration, RemovalPolicy, CfnOutput,
    aws_dynamodb as ddb,
    aws_s3 as s3,
    aws_kms as kms,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_apigateway as apigw,
)
from constructs import Construct

WARDEN_ROOT = Path(__file__).resolve().parents[1]

# Keep the Lambda asset lean: ship core/ + aws/ only.
ASSET_EXCLUDES = [
    "ui", "node_modules", "dist", "tests", "eval", "demo",
    "infra", "*.log", "**/__pycache__", ".pytest_cache", "*.md", "run.sh",
]

RUNTIME = _lambda.Runtime.PYTHON_3_12


class WardenStack(Stack):
    def __init__(self, scope: Construct, cid: str, **kw):
        super().__init__(scope, cid, **kw)

        # ---- state: one DynamoDB table (Backend Schema §2) ------------------
        table = ddb.Table(
            self, "WardenTable", table_name="warden",
            partition_key=ddb.Attribute(name="PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="SK", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",           # expires spent nonces
            removal_policy=RemovalPolicy.DESTROY,
        )
        table.add_global_secondary_index(
            index_name="GSI1",
            partition_key=ddb.Attribute(name="GSI1PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI1SK", type=ddb.AttributeType.STRING),
        )

        # ---- blobs: transcripts + replay artifacts --------------------------
        bucket = s3.Bucket(
            self, "WardenBlobs",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True,
        )

        # ---- the moat: two independent KMS asymmetric keys ------------------
        key_a = kms.Key(
            self, "KeyA", alias="warden/key-a-rehearsal",
            description="WARDEN KEY_A — REHEARSAL_PASS. Only the Sandbox may Sign.",
            key_spec=kms.KeySpec.ECC_NIST_P256, key_usage=kms.KeyUsage.SIGN_VERIFY,
            removal_policy=RemovalPolicy.DESTROY,
        )
        key_b = kms.Key(
            self, "KeyB", alias="warden/key-b-approval",
            description="WARDEN KEY_B — HUMAN_APPROVAL. Only the Approval path may Sign.",
            key_spec=kms.KeySpec.ECC_NIST_P256, key_usage=kms.KeyUsage.SIGN_VERIFY,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ---- code + optional deps layer -------------------------------------
        code = _lambda.Code.from_asset(str(WARDEN_ROOT), exclude=ASSET_EXCLUDES)
        base_env = {
            "WARDEN_TABLE": table.table_name,
            "WARDEN_BUCKET": bucket.bucket_name,
            "KEY_A_ARN": key_a.key_arn,
            "KEY_B_ARN": key_b.key_arn,
        }
        deps_layer = None
        layer_python = WARDEN_ROOT / "infra" / "layers" / "python"
        if layer_python.exists():
            deps_layer = _lambda.LayerVersion(
                self, "Deps",
                code=_lambda.Code.from_asset(str(layer_python.parent)),
                compatible_runtimes=[RUNTIME],
                description="cryptography + shared runtime deps (see infra/build_layer.sh)",
            )

        def mk(cid_: str, handler: str, timeout: int = 30, mem: int = 256) -> _lambda.Function:
            f = _lambda.Function(
                self, cid_, runtime=RUNTIME, handler=handler, code=code,
                timeout=Duration.seconds(timeout), memory_size=mem,
                environment=dict(base_env),
            )
            if deps_layer:
                f.add_layers(deps_layer)
            return f

        # ---- the five services + approval + api -----------------------------
        ingest = mk("Ingest", "aws.lambdas.ingest.handler")
        bucket.grant_read_write(ingest)

        detector = mk("Detector", "aws.lambdas.detector.handler")
        table.grant_read_write_data(detector); bucket.grant_read(detector)

        diagnosis = mk("Diagnosis", "aws.lambdas.diagnosis.handler", timeout=60, mem=512)
        table.grant_read_write_data(diagnosis); bucket.grant_read(diagnosis)
        # NOTE: diagnosis gets NO kms grant — falsify never signs.

        validate = mk("SandboxValidate", "aws.lambdas.sandbox_validate.handler", timeout=60, mem=512)
        table.grant_read_write_data(validate); bucket.grant_read_write(validate)
        key_a.grant(validate, "kms:Sign")                       # KEY_A sign — SANDBOX ONLY

        request_approval = mk("RequestApproval", "aws.lambdas.request_approval.handler")
        table.grant_read_write_data(request_approval)

        approval = mk("Approval", "aws.lambdas.approval.handler")
        table.grant_read_write_data(approval)
        key_b.grant(approval, "kms:Sign")                       # KEY_B sign — APPROVAL ONLY
        approval.add_to_role_policy(iam.PolicyStatement(
            actions=["states:SendTaskSuccess", "states:SendTaskFailure"], resources=["*"]))

        actuator = mk("Actuator", "aws.lambdas.actuator.handler")
        table.grant_read_write_data(actuator)
        for k in (key_a, key_b):
            k.grant(actuator, "kms:Verify", "kms:GetPublicKey")  # VERIFY ONLY — no Sign
        # ^ the enforced "actuator cannot self-authorize" property.

        # ---- the saga (Step Functions) --------------------------------------
        detect_t = tasks.LambdaInvoke(
            self, "DetectStep", lambda_function=detector, payload_response_only=True,
            payload=sfn.TaskInput.from_object({"sessionId": sfn.JsonPath.string_at("$.sessionId")}),
            result_path="$")
        diagnose_t = tasks.LambdaInvoke(
            self, "DiagnoseStep", lambda_function=diagnosis, payload_response_only=True,
            payload=sfn.TaskInput.from_object({
                "caseId": sfn.JsonPath.string_at("$.caseId"),
                "sessionId": sfn.JsonPath.string_at("$.sessionId")}),
            result_path="$.diagnosis")
        validate_t = tasks.LambdaInvoke(
            self, "ValidateStep", lambda_function=validate, payload_response_only=True,
            payload=sfn.TaskInput.from_object({
                "caseId": sfn.JsonPath.string_at("$.caseId"),
                "sessionId": sfn.JsonPath.string_at("$.sessionId")}),
            result_path="$.rehearsal")
        request_approval_t = tasks.LambdaInvoke(
            self, "RequestApprovalStep", lambda_function=request_approval,
            integration_pattern=sfn.IntegrationPattern.WAIT_FOR_TASK_TOKEN,
            payload=sfn.TaskInput.from_object({
                "caseId": sfn.JsonPath.string_at("$.caseId"),
                "canonical": sfn.JsonPath.string_at("$.rehearsal.canonical"),
                "sandboxRunId": sfn.JsonPath.string_at("$.rehearsal.sandboxRunId"),
                "taskToken": sfn.JsonPath.task_token}),
            result_path="$.approval")
        execute_t = tasks.LambdaInvoke(
            self, "ExecuteStep", lambda_function=actuator, payload_response_only=True,
            payload=sfn.TaskInput.from_object({
                "caseId": sfn.JsonPath.string_at("$.caseId"),
                "tokenA": sfn.JsonPath.string_at("$.rehearsal.tokenA"),
                "tokenB": sfn.JsonPath.string_at("$.approval.tokenB")}),
            result_path="$.actuation")

        no_misbehavior = sfn.Succeed(self, "NoMisbehavior")
        escalate = sfn.Fail(self, "Escalate", error="RehearsalFailed",
                            cause="validation did not clear the fault")
        resolved = sfn.Succeed(self, "Resolved")
        refused = sfn.Fail(self, "Refused", error="ActuationRefused",
                          cause="missing/invalid attestation — nothing deployed")

        applied_choice = sfn.Choice(self, "Applied?").when(
            sfn.Condition.string_equals("$.actuation.status", "applied"), resolved).otherwise(refused)
        signed_choice = sfn.Choice(self, "Rehearsed?").when(
            sfn.Condition.boolean_equals("$.rehearsal.signed", True),
            request_approval_t.next(execute_t).next(applied_choice)).otherwise(escalate)
        detected_choice = sfn.Choice(self, "Detected?").when(
            sfn.Condition.boolean_equals("$.detected", True),
            diagnose_t.next(validate_t).next(signed_choice)).otherwise(no_misbehavior)

        definition = detect_t.next(detected_choice)
        state_machine = sfn.StateMachine(
            self, "WardenSaga", definition_body=sfn.DefinitionBody.from_chainable(definition),
            timeout=Duration.hours(1))

        # ---- REST API (thin BFF; no crypto grants of its own) ---------------
        api_fn = mk("Api", "aws.lambdas.api.handler")
        table.grant_read_data(api_fn)
        approval.grant_invoke(api_fn); actuator.grant_invoke(api_fn)
        api_fn.add_environment("APPROVAL_FN", approval.function_name)
        api_fn.add_environment("ACTUATOR_FN", actuator.function_name)
        api = apigw.LambdaRestApi(self, "WardenApi", handler=api_fn, proxy=True,
                                  deploy_options=apigw.StageOptions(stage_name="prod"))

        # ---- outputs --------------------------------------------------------
        CfnOutput(self, "TableName", value=table.table_name)
        CfnOutput(self, "BlobsBucket", value=bucket.bucket_name)
        CfnOutput(self, "KeyAArn", value=key_a.key_arn)
        CfnOutput(self, "KeyBArn", value=key_b.key_arn)
        CfnOutput(self, "SagaArn", value=state_machine.state_machine_arn)
        CfnOutput(self, "ApiUrl", value=api.url)
