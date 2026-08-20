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


def test_websocket_connect_requires_one_time_ticket_authorizer():
    resources = _template()["Resources"]
    route = resources["WebSocketConnectRoute"]["Properties"]
    authorizer = resources["WebSocketAuthorizer"]["Properties"]
    ticket_table = resources["WebSocketTicketsTable"]["Properties"]

    assert route["AuthorizationType"] == "CUSTOM"
    assert route["AuthorizerId"] == {"Ref": "WebSocketAuthorizer"}
    assert authorizer["AuthorizerType"] == "REQUEST"
    assert authorizer["AuthorizerResultTtlInSeconds"] == 0
    assert authorizer["IdentitySource"] == [
        "route.request.querystring.ticket"
    ]
    assert ticket_table["TimeToLiveSpecification"] == {
        "AttributeName": "ttl",
        "Enabled": True,
    }


def test_metrics_and_websocket_ticket_routes_inherit_cognito_auth():
    resources = _template()["Resources"]
    metrics_events = resources["MetricsHandlerFunction"]["Properties"]["Events"]
    auth_events = resources["AuthHandlerFunction"]["Properties"]["Events"]

    assert "Auth" not in metrics_events["RealtimeMetrics"]["Properties"]
    assert "Auth" not in metrics_events["PrometheusMetrics"]["Properties"]
    assert "Auth" not in auth_events["WebSocketTicket"]["Properties"]
    assert auth_events["Login"]["Properties"]["Auth"] == {"Authorizer": "NONE"}


def test_integration_secret_access_is_exact_and_function_scoped():
    resources = _template()["Resources"]
    platform_policy = resources["PlatformIntegrationSecretReadPolicy"]
    partner_policy = resources["PartnerIntelSecretReadPolicy"]

    platform_statement = platform_policy["Properties"]["PolicyDocument"]["Statement"][0]
    partner_statement = partner_policy["Properties"]["PolicyDocument"]["Statement"][0]
    assert platform_statement == {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": {"Ref": "PlatformAuthSecretArn"},
    }
    assert partner_statement == {
        "Effect": "Allow",
        "Action": ["secretsmanager:GetSecretValue"],
        "Resource": {"Ref": "PartnerIntelAuthSecretArn"},
    }

    platform_kms = platform_policy["Properties"]["PolicyDocument"]["Statement"][1][
        "If"
    ][1]
    partner_kms = partner_policy["Properties"]["PolicyDocument"]["Statement"][1][
        "If"
    ][1]
    assert platform_kms["Action"] == ["kms:Decrypt"]
    assert platform_kms["Resource"] == {"Ref": "PlatformAuthKmsKeyArn"}
    assert platform_kms["Condition"]["StringEquals"]["kms:ViaService"] == {
        "Sub": "secretsmanager.${AWS::Region}.${AWS::URLSuffix}"
    }
    assert partner_kms["Action"] == ["kms:Decrypt"]
    assert partner_kms["Resource"] == {"Ref": "PartnerIntelAuthKmsKeyArn"}

    functions = {
        name: resource["Properties"]
        for name, resource in resources.items()
        if resource["Type"] == "AWS::Serverless::Function"
    }
    platform_consumers = {
        name
        for name, properties in functions.items()
        if _references(
            "PlatformIntegrationSecretReadPolicy",
            properties.get("Policies", []),
        )
    }
    partner_consumers = {
        name
        for name, properties in functions.items()
        if _references(
            "PartnerIntelSecretReadPolicy",
            properties.get("Policies", []),
        )
    }

    assert platform_consumers == {
        "EnforcementHandlerFunction",
        "ReviewHandlerFunction",
        "ProfileProcessorFunction",
        "NotificationProcessorFunction",
        "EvidenceAssemblerFunction",
        "EnforcementExecutorFunction",
    }
    assert partner_consumers == {"IntelligenceHandlerFunction"}

    platform_configured = {
        name
        for name, properties in functions.items()
        if "PLATFORM_AUTH_SECRET_ARN"
        in properties.get("Environment", {}).get("Variables", {})
    }
    partner_configured = {
        name
        for name, properties in functions.items()
        if "PARTNER_INTEL_AUTH_SECRET_ARN"
        in properties.get("Environment", {}).get("Variables", {})
    }
    assert platform_configured == platform_consumers
    assert partner_configured == partner_consumers


def test_websocket_ticket_table_is_exposed_only_to_ticket_functions():
    resources = _template()["Resources"]
    functions = {
        name: resource["Properties"]
        for name, resource in resources.items()
        if resource["Type"] == "AWS::Serverless::Function"
    }
    configured = {
        name
        for name, properties in functions.items()
        if "WEBSOCKET_TICKETS_TABLE"
        in properties.get("Environment", {}).get("Variables", {})
    }

    assert configured == {
        "AuthHandlerFunction",
        "WebSocketAuthorizerFunction",
    }


def test_production_requires_secret_backed_integration_auth():
    template = _template()
    parameters = template["Parameters"]
    assertions = template["Rules"]["ProductionIntegrationConfiguration"][
        "Assertions"
    ]

    assert parameters["PlatformAuthMode"]["Default"] == "none"
    assert parameters["PartnerIntelAuthMode"]["Default"] == "none"
    descriptions = {assertion["AssertDescription"] for assertion in assertions}
    assert "Production deployments require platform API authentication" in descriptions
    assert "Production deployments require a platform API secret ARN" in descriptions
    assert (
        "Production deployments require partner intelligence authentication"
        in descriptions
    )
    assert (
        "Production deployments require a partner intelligence secret ARN"
        in descriptions
    )
