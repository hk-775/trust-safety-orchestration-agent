"""Delete a deployed stack after safely emptying managed S3 buckets."""

import argparse
import os
import sys
from collections.abc import Iterable

import boto3
from botocore.exceptions import ClientError, WaiterError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete a deployed SafetyAgent stack")
    parser.add_argument(
        "--env",
        default="dev",
        choices=["dev", "staging", "prodtest", "prod"],
    )
    parser.add_argument("--region", default=os.environ.get("AWS_REGION"))
    parser.add_argument("--stack-name")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required to delete a production stack",
    )
    return parser.parse_args()


def chunks(items: list[dict[str, str]], size: int = 1000) -> Iterable[list[dict[str, str]]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def delete_objects(
    s3_client,
    bucket_name: str,
    objects: list[dict[str, str]],
) -> None:
    for batch in chunks(objects):
        s3_client.delete_objects(
            Bucket=bucket_name,
            Delete={"Objects": batch, "Quiet": True},
        )


def empty_bucket(s3_client, bucket_name: str) -> None:
    print(f"Emptying s3://{bucket_name}...")

    while True:
        page = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=1000)
        versioned_objects = [
            {"Key": item["Key"], "VersionId": item["VersionId"]}
            for item in page.get("Versions", []) + page.get("DeleteMarkers", [])
        ]
        if not versioned_objects:
            break
        delete_objects(s3_client, bucket_name, versioned_objects)

    while True:
        page = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1000)
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if not objects:
            break
        delete_objects(s3_client, bucket_name, objects)


def stack_outputs(stack: dict) -> dict[str, str]:
    return {
        output["OutputKey"]: output["OutputValue"]
        for output in stack.get("Outputs", [])
    }


def managed_bucket_output_keys(environment: str) -> list[str]:
    keys = ["FrontendBucketName"]
    if environment != "prod":
        keys.extend(
            [
                "EvidenceBucketName",
                "AuditBucketName",
                "ConfigBackupsBucketName",
                "AccessLogsBucketName",
            ]
        )
    return keys


def main() -> int:
    args = parse_args()
    stack_name = args.stack_name or f"trust-safety-orch-{args.env}"

    session = boto3.Session(region_name=args.region)
    cloudformation = session.client("cloudformation")
    s3 = session.client("s3")

    try:
        stack = cloudformation.describe_stacks(StackName=stack_name)["Stacks"][0]
    except ClientError as error:
        if error.response["Error"]["Code"] == "ValidationError":
            print(f"Stack does not exist: {stack_name}")
            return 0
        raise

    deployed_environment = next(
        (
            parameter["ParameterValue"]
            for parameter in stack.get("Parameters", [])
            if parameter["ParameterKey"] == "Environment"
        ),
        args.env,
    )
    if deployed_environment != args.env:
        print(
            f"ERROR: Stack environment is {deployed_environment}, not {args.env}.",
            file=sys.stderr,
        )
        return 1
    if deployed_environment == "prod" and not args.allow_production:
        print(
            "ERROR: Refusing to delete production without --allow-production.",
            file=sys.stderr,
        )
        return 1

    outputs = stack_outputs(stack)
    for output_key in managed_bucket_output_keys(deployed_environment):
        bucket_name = outputs.get(output_key)
        if not bucket_name:
            continue
        try:
            empty_bucket(s3, bucket_name)
        except ClientError as error:
            if error.response["Error"]["Code"] != "NoSuchBucket":
                raise

    print(f"Deleting CloudFormation stack {stack_name}...")
    cloudformation.delete_stack(StackName=stack_name)
    try:
        cloudformation.get_waiter("stack_delete_complete").wait(StackName=stack_name)
    except WaiterError as error:
        print(f"ERROR: Stack deletion failed: {error}", file=sys.stderr)
        return 1

    print(f"Deleted stack {stack_name}.")
    if deployed_environment == "prod":
        print("Production evidence, audit, configuration, and core data resources were retained.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClientError as error:
        code = error.response["Error"]["Code"]
        message = error.response["Error"]["Message"]
        print(f"ERROR: AWS request failed ({code}): {message}", file=sys.stderr)
        raise SystemExit(1)
