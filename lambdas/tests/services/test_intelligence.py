import hashlib
import json
from unittest.mock import MagicMock, patch

from services import intelligence_service as svc


class TestHashGeneration:
    def test_fingerprint_hash_deterministic(self):
        fp = {"device_id": "abc", "browser": "chrome"}
        h1 = svc.generate_fingerprint_hash(fp)
        h2 = svc.generate_fingerprint_hash(fp)
        assert h1 == h2
        assert len(h1) == 64

    def test_fingerprint_hash_uses_sha256(self):
        fp = {"device_id": "test"}
        expected = hashlib.sha256(json.dumps(fp, sort_keys=True).encode()).hexdigest()
        assert svc.generate_fingerprint_hash(fp) == expected

    def test_different_inputs_different_hashes(self):
        h1 = svc.generate_fingerprint_hash({"a": 1})
        h2 = svc.generate_fingerprint_hash({"a": 2})
        assert h1 != h2

    def test_behavioral_signature_hash(self):
        sig = {"pattern": "rapid_messaging", "score": 0.8}
        h = svc.generate_behavioral_signature_hash(sig)
        assert len(h) == 64


class TestCheckBlocklistMatch:
    @patch("repositories.blocklist_repository.check_fingerprint")
    def test_fingerprint_match(self, mock_check):
        mock_check.return_value = {
            "confidence_score": 0.95,
            "source_platform": "partner_a",
            "ban_reason": "scam",
        }
        result = svc.check_blocklist_match("hash123")
        assert result is not None
        assert result["match_type"] == "fingerprint"
        assert result["confidence"] == 0.95

    @patch("repositories.blocklist_repository.check_signature")
    @patch("repositories.blocklist_repository.check_fingerprint")
    def test_signature_fallback(self, mock_fp, mock_sig):
        mock_fp.return_value = None
        mock_sig.return_value = {
            "confidence_score": 0.8,
            "source_platform": "partner_b",
            "ban_reason": "harassment",
        }
        result = svc.check_blocklist_match("hash123", "sig456")
        assert result is not None
        assert result["match_type"] == "behavioral_signature"

    @patch("repositories.blocklist_repository.check_fingerprint")
    def test_no_match(self, mock_fp):
        mock_fp.return_value = None
        result = svc.check_blocklist_match("hash123")
        assert result is None

    @patch("repositories.blocklist_repository.check_fingerprint")
    def test_dict_fingerprint_hashed(self, mock_fp):
        mock_fp.return_value = None
        svc.check_blocklist_match({"device_id": "test"})
        called_hash = mock_fp.call_args[0][0]
        assert len(called_hash) == 64


class TestIngestExternalIntelligence:
    @patch("repositories.audit_repository.write_log")
    @patch("repositories.blocklist_repository.add_bad_actor")
    def test_successful_ingest(self, mock_add, mock_audit):
        actors = [
            {"fingerprint_hash": "h1", "ban_reason": "scam"},
            {"fingerprint_hash": "h2", "ban_reason": "harassment"},
        ]
        result = svc.ingest_external_intelligence("partner_a", actors)
        assert result["processed_count"] == 2
        assert result["error_count"] == 0
        assert mock_add.call_count == 2

    @patch("repositories.audit_repository.write_log")
    @patch("repositories.blocklist_repository.add_bad_actor", side_effect=Exception("db error"))
    def test_partial_failure(self, mock_add, mock_audit):
        actors = [{"fingerprint_hash": "h1"}]
        result = svc.ingest_external_intelligence("partner_a", actors)
        assert result["error_count"] == 1
        assert result["processed_count"] == 0


class TestValidateNoPii:
    def test_clean_payload_passes(self):
        payload = {
            "bad_actors": [
                {"fingerprint_hash": "abc", "ban_reason": "scam", "ban_timestamp": "2024-01-01"}
            ]
        }
        svc._validate_no_pii(payload)

    def test_extra_fields_with_pii_indicator_raises(self):
        payload = {
            "bad_actors": [
                {"fingerprint_hash": "abc", "email": "user@test.com", "ban_reason": "scam"}
            ]
        }
        import pytest
        with pytest.raises(ValueError, match="Potential PII"):
            svc._validate_no_pii(payload)


class TestPublishBadActor:
    @patch("urllib.request.urlopen")
    @patch("repositories.audit_repository.write_log")
    @patch(
        "services.intelligence_service.PARTNER_NETWORK_INTEL_API_URL",
        "https://intel.partner.test/v1",
    )
    def test_publish_uses_https_integration_url(self, mock_audit, mock_urlopen):
        response = MagicMock()
        response.read.return_value = b'{"accepted": true}'
        response.__enter__.return_value = response
        mock_urlopen.return_value = response

        result = svc.publish_bad_actor("user-1", "fingerprint", "signature", "scam")

        request = mock_urlopen.call_args.args[0]
        assert request.full_url == "https://intel.partner.test/v1/intelligence/ingest"
        assert result["published"] is True
        mock_audit.assert_called_once()

    @patch(
        "services.intelligence_service.PARTNER_NETWORK_INTEL_API_URL",
        "http://intel.partner.test/v1",
    )
    def test_publish_rejects_non_https_url(self):
        result = svc.publish_bad_actor("user-1", "fingerprint", "signature", "scam")

        assert result["published"] is False
        assert "must be HTTPS" in result["reason"]
