import os
from decimal import Decimal

import boto3
from functools import lru_cache


@lru_cache(maxsize=1)
def get_dynamodb_resource():
    return boto3.resource("dynamodb")


@lru_cache(maxsize=1)
def get_s3_client():
    return boto3.client("s3")


def get_table(env_var: str):
    table_name = os.environ[env_var]
    return get_dynamodb_resource().Table(table_name)


def get_bucket_name(env_var: str) -> str:
    return os.environ[env_var]


def to_dynamodb_types(value):
    """Recursively convert Python floats into DynamoDB-compatible decimals."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: to_dynamodb_types(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_dynamodb_types(item) for item in value]
    if isinstance(value, set):
        return {to_dynamodb_types(item) for item in value}
    return value
