from scripts.delete_stack import empty_bucket, managed_bucket_output_keys


class FakeS3Client:
    def __init__(self):
        self.version_responses = [
            {
                "Versions": [{"Key": "evidence.json", "VersionId": "v1"}],
                "DeleteMarkers": [{"Key": "removed.json", "VersionId": "v2"}],
            },
            {},
        ]
        self.object_responses = [
            {"Contents": [{"Key": "current.json"}]},
            {},
        ]
        self.deleted = []

    def list_object_versions(self, **kwargs):
        assert kwargs == {"Bucket": "test-bucket", "MaxKeys": 1000}
        return self.version_responses.pop(0)

    def list_objects_v2(self, **kwargs):
        assert kwargs == {"Bucket": "test-bucket", "MaxKeys": 1000}
        return self.object_responses.pop(0)

    def delete_objects(self, **kwargs):
        self.deleted.append(kwargs)


def test_empty_bucket_removes_versions_markers_and_current_objects():
    client = FakeS3Client()

    empty_bucket(client, "test-bucket")

    assert client.deleted == [
        {
            "Bucket": "test-bucket",
            "Delete": {
                "Objects": [
                    {"Key": "evidence.json", "VersionId": "v1"},
                    {"Key": "removed.json", "VersionId": "v2"},
                ],
                "Quiet": True,
            },
        },
        {
            "Bucket": "test-bucket",
            "Delete": {
                "Objects": [{"Key": "current.json"}],
                "Quiet": True,
            },
        },
    ]


def test_non_production_teardown_includes_access_logs_bucket():
    assert managed_bucket_output_keys("prodtest") == [
        "FrontendBucketName",
        "EvidenceBucketName",
        "AuditBucketName",
        "ConfigBackupsBucketName",
        "AccessLogsBucketName",
    ]


def test_production_teardown_only_empties_frontend_bucket():
    assert managed_bucket_output_keys("prod") == ["FrontendBucketName"]
