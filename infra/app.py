#!/usr/bin/env python3
"""WARDEN — CDK app entry. Region defaults to ap-south-1 (Mumbai) per the tech
stack (low latency + AgentCore availability); override with CDK_DEFAULT_REGION."""
import os
import sys

# Make the warden root importable so `warden_stack` can pull core/aws if needed.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aws_cdk as cdk
from warden_stack import WardenStack

app = cdk.App()
WardenStack(
    app, "WardenStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "ap-south-1"),
    ),
    description="WARDEN — antivirus for autonomous AI agents (provable cause, unforgeable fix).",
)
app.synth()
