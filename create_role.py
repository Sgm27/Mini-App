"""
Create IAM role for Lambda execution and save result to JSON.
Usage: python create_role.py
"""

import json
import time
import os

import boto3
from dotenv import load_dotenv

load_dotenv(override=True)

REGION = "ap-southeast-1"
ROLE_NAME = "lambda-basic-execution-role"

TRUST_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}

REQUIRED_POLICIES = [
    "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    "arn:aws:iam::aws:policy/AmazonS3FullAccess",
]


def main():
    session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=REGION,
    )
    iam = session.client("iam")

    created = False
    try:
        resp = iam.get_role(RoleName=ROLE_NAME)
        role_arn = resp["Role"]["Arn"]
        print(f"Role already exists: {role_arn}")
    except iam.exceptions.NoSuchEntityException:
        resp = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(TRUST_POLICY),
            Description="Basic execution role for Lambda functions",
        )
        role_arn = resp["Role"]["Arn"]
        created = True
        print(f"Created role: {role_arn}")
        print("Waiting 10s for IAM propagation...")
        time.sleep(10)

    # Ensure required policies are attached
    attached = {
        p["PolicyArn"]
        for p in iam.list_attached_role_policies(RoleName=ROLE_NAME)["AttachedPolicies"]
    }
    attached_policies = []
    for policy_arn in REQUIRED_POLICIES:
        if policy_arn not in attached:
            iam.attach_role_policy(RoleName=ROLE_NAME, PolicyArn=policy_arn)
            print(f"Attached: {policy_arn}")
        else:
            print(f"Already attached: {policy_arn}")
        attached_policies.append(policy_arn)

    # Save result to JSON
    result = {
        "role_name": ROLE_NAME,
        "role_arn": role_arn,
        "created": created,
        "attached_policies": attached_policies,
    }

    output_file = "iam_role.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nResult saved to {output_file}")


if __name__ == "__main__":
    main()
