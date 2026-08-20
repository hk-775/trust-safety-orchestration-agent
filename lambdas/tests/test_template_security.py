from pathlib import Path

import yaml
from yaml.nodes import MappingNode, ScalarNode, SequenceNode


class CloudFormationLoader(yaml.SafeLoader):
    pass


def _construct_intrinsic(loader, tag_suffix, node):
    if isinstance(node, ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, SequenceNode):
        value = loader.construct_sequence(node)
    elif isinstance(node, MappingNode):
        value = loader.construct_mapping(node)
    else:
        raise TypeError(f"Unsupported YAML node: {type(node)}")
    return {tag_suffix: value}


CloudFormationLoader.add_multi_constructor("!", _construct_intrinsic)


def _template():
    template_path = Path(__file__).parents[2] / "template.yaml"
    return yaml.load(template_path.read_text(), Loader=CloudFormationLoader)


def _references(logical_id, value):
    if isinstance(value, dict):
        return value.get("Ref") == logical_id or any(
            _references(logical_id, child) for child in value.values()
        )
    if isinstance(value, list):
        return any(_references(logical_id, child) for child in value)
    return False


def test_vpc_permissions_are_limited_to_vpc_functions():
    resources = _template()["Resources"]
    functions = {
        name: resource["Properties"]
        for name, resource in resources.items()
        if resource["Type"] == "AWS::Serverless::Function"
    }

    vpc_functions = {
        name for name, properties in functions.items() if "VpcConfig" in properties
    }
    vpc_policy_functions = {
        name
        for name, properties in functions.items()
        if _references("SafetyAgentVpcPolicy", properties.get("Policies", []))
    }

    assert vpc_policy_functions == vpc_functions


def test_base_policy_does_not_grant_ec2_network_access():
    resources = _template()["Resources"]
    base_policy = resources["SafetyAgentBasePolicy"]["Properties"]
    statements = base_policy["PolicyDocument"]["Statement"]
    actions = {
        action
        for statement in statements
        for action in statement.get("Action", [])
    }

    assert not any(action.startswith("ec2:") for action in actions)
    assert "ManagedPolicyName" not in base_policy


def test_vpc_policy_is_conditional_and_scoped_to_eni_operations():
    vpc_policy = _template()["Resources"]["SafetyAgentVpcPolicy"]
    actions = set(vpc_policy["Properties"]["PolicyDocument"]["Statement"][0]["Action"])

    assert vpc_policy["Condition"] == "EnableRedis"
    assert actions == {
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DetachNetworkInterface",
    }


def test_globally_named_resources_include_region_and_account():
    resources = _template()["Resources"]

    for logical_id in (
        "AccessLogsBucket",
        "EvidenceStoreBucket",
        "AuditArchiveBucket",
        "ConfigBackupsBucket",
        "FrontendBucket",
    ):
        bucket_name = resources[logical_id]["Properties"]["BucketName"]["Sub"]
        assert "${AWS::Region}" in bucket_name
        assert "${AWS::AccountId}" in bucket_name

    cloudfront_names = (
        resources["CloudFrontOAC"]["Properties"]["OriginAccessControlConfig"]["Name"],
        resources["FrontendSpaRewriteFunction"]["Properties"]["Name"],
        resources["FrontendSecurityHeadersPolicy"]["Properties"][
            "ResponseHeadersPolicyConfig"
        ]["Name"],
    )
    for name in cloudfront_names:
        value = name["Sub"]
        assert "${AWS::Region}" in value
        assert "${AWS::AccountId}" in value
