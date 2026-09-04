"""Unit tests for Dual RBAC Authentication and Metrics Endpoints."""

import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.main import app
from backend import config


class TestRBACSecurity(unittest.TestCase):
    """Test suite for Role-Based Access Control and API Key tiers."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_unauthenticated_access_rejected(self):
        """Unauthenticated requests to protected endpoints should return 401."""
        res_root = self.client.get("/")
        self.assertEqual(res_root.status_code, 401)
        self.assertIn("WWW-Authenticate", res_root.headers)

        res_dash = self.client.get("/dashboard")
        self.assertEqual(res_dash.status_code, 401)
        self.assertIn("WWW-Authenticate", res_dash.headers)

    def test_clinician_access_consultation_allowed(self):
        """Clinician user credentials should grant access to root consultation UI."""
        res = self.client.get("/", auth=(config.USER_USER, config.USER_PASS))
        self.assertEqual(res.status_code, 200)

    def test_clinician_access_dashboard_forbidden(self):
        """Clinician user credentials attempting to access dashboard should return 403 Forbidden."""
        res = self.client.get("/dashboard", auth=(config.USER_USER, config.USER_PASS))
        self.assertEqual(res.status_code, 403)
        self.assertIn("Admin privileges required", res.json().get("detail", ""))

    def test_admin_access_both_allowed(self):
        """Administrator credentials should grant access to both consultation UI and dashboard."""
        res_root = self.client.get("/", auth=(config.ADMIN_USER, config.ADMIN_PASS))
        self.assertEqual(res_root.status_code, 200)

        res_dash = self.client.get("/dashboard", auth=(config.ADMIN_USER, config.ADMIN_PASS))
        self.assertEqual(res_dash.status_code, 200)

    def test_invalid_credentials_rejected(self):
        """Invalid username or password should return 401."""
        res = self.client.get("/", auth=("wrong_user", "wrong_pass"))
        self.assertEqual(res.status_code, 401)

    def test_admin_metrics_endpoint_with_admin_key(self):
        """Admin metrics endpoint should return full telemetry when called with Admin API key."""
        # Test with header
        res_hdr = self.client.get("/api/metrics", headers={"x-api-key": config.ADMIN_API_KEY})
        self.assertEqual(res_hdr.status_code, 200)
        data = res_hdr.json()
        self.assertEqual(data.get("authenticated_role"), "admin")
        self.assertIn("rate_limiter_live", data)
        self.assertIn("telemetry", data)

        # Test with query parameter (?api_key=...)
        res_param = self.client.get(f"/api/metrics?api_key={config.ADMIN_API_KEY}")
        self.assertEqual(res_param.status_code, 200)
        self.assertEqual(res_param.json().get("authenticated_role"), "admin")

    def test_admin_metrics_endpoint_rejects_user_key(self):
        """Admin metrics endpoint should reject regular user / demo API key with 403."""
        res = self.client.get("/api/metrics", headers={"x-api-key": config.USER_API_KEY})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Admin Dashboard API Key", res.json().get("detail", ""))

    def test_admin_metrics_endpoint_rejects_unauthenticated(self):
        """Admin metrics endpoint without key should return 401."""
        res = self.client.get("/api/metrics")
        self.assertEqual(res.status_code, 401)

    def test_admin_verify_endpoint_with_active_admin_key(self):
        """Admin verify endpoint should return 200 authorized for valid admin key."""
        res = self.client.post("/api/admin/verify", headers={"x-api-key": config.ADMIN_API_KEY})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "authorized")
        self.assertEqual(data.get("role"), "admin")

    def test_admin_verify_endpoint_rejects_clinical_user_key(self):
        """Admin verify endpoint must reject standard clinician key with 403 Forbidden."""
        res = self.client.post("/api/admin/verify", headers={"x-api-key": config.USER_API_KEY})
        self.assertEqual(res.status_code, 403)
        self.assertIn("Admin Dashboard API Key", res.json().get("detail", ""))

    def test_admin_verify_endpoint_rejects_unauthenticated(self):
        """Admin verify endpoint without key should return 401."""
        res = self.client.post("/api/admin/verify")
        self.assertEqual(res.status_code, 401)

    def test_dual_key_rotation_admin_grace_period(self):
        """Admin endpoints should accept PREVIOUS_ADMIN_API_KEY during rotation transition."""
        from unittest.mock import patch
        with patch("backend.security.PREVIOUS_ADMIN_API_KEY", "predoc_admin_previous_grace_key_456"):
            # Test verify with previous rotated admin key
            res_verify = self.client.post(
                "/api/admin/verify",
                headers={"x-api-key": "predoc_admin_previous_grace_key_456"}
            )
            self.assertEqual(res_verify.status_code, 200)

            # Test metrics with previous rotated admin key
            res_metrics = self.client.get(
                "/api/metrics",
                headers={"x-api-key": "predoc_admin_previous_grace_key_456"}
            )
            self.assertEqual(res_metrics.status_code, 200)

    def test_system_retrieval_requires_admin_key(self):
        """Switching retrieval mode must require valid Admin key, rejecting unauthenticated & clinician keys."""
        # 1. Unauthenticated request rejected
        res_unauth = self.client.post("/api/system/retrieval", json={"mode": "hybrid"})
        self.assertEqual(res_unauth.status_code, 401)

        # 2. Clinician key rejected with 403 Forbidden
        res_user = self.client.post(
            "/api/system/retrieval",
            headers={"x-api-key": config.USER_API_KEY},
            json={"mode": "hybrid"}
        )
        self.assertEqual(res_user.status_code, 403)

        # 3. Valid Admin key accepted
        res_admin = self.client.post(
            "/api/system/retrieval",
            headers={"x-api-key": config.ADMIN_API_KEY},
            json={"mode": "hybrid"}
        )
        self.assertEqual(res_admin.status_code, 200)
        data = res_admin.json()
        self.assertEqual(data.get("mode"), "hybrid")
        self.assertEqual(data.get("updated_by"), "admin")


if __name__ == "__main__":
    unittest.main()

