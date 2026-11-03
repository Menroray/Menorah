import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backend import backend
import webapp
from database import database


class PublicDemoWebAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = webapp.app.test_client()

    def test_web_app_uses_separate_demo_database(self):
        self.assertEqual(database.DB_PATH, webapp.WEB_DB_PATH)
        self.assertNotEqual(database.DB_PATH, Path(__file__).resolve().parents[1] / "school_fees.db")

    def test_health_check(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})

    def test_dashboard_and_student_ledger_show_demo_records(self):
        dashboard = self.client.get("/")
        ledger = self.client.get("/students")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(ledger.status_code, 200)
        self.assertIn(b"Public demo", dashboard.data)
        self.assertIn(b"Ama Demo", ledger.data)
        self.assertNotIn(b"name=\"full_name\"", ledger.data)

    def test_public_demo_disables_writes_and_admin_login(self):
        response = self.client.post("/students/add")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/login").status_code, 404)

    def test_student_payment_receipt_renders(self):
        detail = self.client.get("/students/1")
        response = self.client.get("/payments/1/receipt")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Ama Demo", detail.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Payment received", response.data)

    def test_private_mode_requires_login_and_supports_student_payment_flow(self):
        original_db_path = database.DB_PATH
        original_backend_db_path = backend.DB_PATH
        config_keys = (
            "DEMO_MODE",
            "READ_ONLY_DEMO",
            "WEB_ADMIN_USERNAME",
            "WEB_ADMIN_PASSWORD",
            "SECRET_KEY",
        )
        original_config = {key: webapp.app.config[key] for key in config_keys}

        with TemporaryDirectory() as temporary_directory:
            isolated_db = Path(temporary_directory) / "private.db"
            database.DB_PATH = isolated_db
            backend.DB_PATH = isolated_db
            database.init_db()
            webapp.app.config.update(
                DEMO_MODE=False,
                READ_ONLY_DEMO=False,
                WEB_ADMIN_USERNAME="test-admin",
                WEB_ADMIN_PASSWORD="test-only-password",
                SECRET_KEY="test-session-secret",
            )
            client = webapp.app.test_client()
            try:
                self.assertEqual(client.post("/students/add").status_code, 302)
                self.assertEqual(client.get("/login").status_code, 200)

                client.get("/login")
                with client.session_transaction() as browser_session:
                    csrf_token = browser_session["_csrf_token"]
                login_response = client.post(
                    "/login",
                    data={
                        "csrf_token": csrf_token,
                        "username": "test-admin",
                        "password": "test-only-password",
                    },
                )
                self.assertEqual(login_response.status_code, 302)

                with client.session_transaction() as browser_session:
                    csrf_token = browser_session["_csrf_token"]
                add_response = client.post(
                    "/students/add",
                    data={
                        "csrf_token": csrf_token,
                        "full_name": "Private Test Student",
                        "class_grade": "Grade 1",
                        "term_fees_billed": "300",
                    },
                )
                self.assertEqual(add_response.status_code, 302)
                payment_response = client.post(
                    "/students/1/payments/add",
                    data={
                        "csrf_token": csrf_token,
                        "amount": "125",
                        "term": "Term 1",
                        "payment_method": "Cash",
                        "paid_by": "Test Guardian",
                    },
                )
                self.assertEqual(payment_response.status_code, 302)
                receipt = client.get(payment_response.location)
                self.assertEqual(receipt.status_code, 200)
                self.assertIn(b"GH", receipt.data)
            finally:
                webapp.app.config.update(original_config)
                database.DB_PATH = original_db_path
                backend.DB_PATH = original_backend_db_path


if __name__ == "__main__":
    unittest.main()
