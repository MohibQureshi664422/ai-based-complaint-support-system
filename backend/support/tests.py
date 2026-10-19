
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Profile, Complaint


class WorkflowTests(TestCase):

    def setUp(self):
        self.customer = User.objects.create_user(
            "alice", password="TestPass123!"
        )
        Profile.objects.create(user=self.customer)

        self.other = User.objects.create_user(
            "bob", password="TestPass123!"
        )
        Profile.objects.create(user=self.other)

        self.staff = User.objects.create_user(
            "agent", password="TestPass123!"
        )
        Profile.objects.create(
            user=self.staff,
            role="staff",
            department="IT Support"
        )

        self.admin = User.objects.create_user(
            "boss", password="TestPass123!"
        )
        Profile.objects.create(
            user=self.admin,
            role="admin"
        )

        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    # TEST 1: Complete complaint workflow and permissions
    def test_complete_workflow_and_permissions(self):
        response = self.client.post(
            "/api/complaints/",
            {
                "title": "Internet failure",
                "description": "My wifi network connection is not working"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 201)
        cid = response.data["id"]
        self.assertEqual(response.data["department"], "IT Support")

        response = self.client.post(
            f"/api/complaints/{cid}/review/",
            {
                "status": "Resolved",
                "category": "Technical Issue",
                "priority": "Medium"
            },
            format="json"
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(self.other)

        response = self.client.get(f"/api/complaints/{cid}/")
        self.assertEqual(response.status_code, 404)

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            f"/api/complaints/{cid}/review/",
            {
                "status": "Assigned",
                "category": "Technical Issue",
                "priority": "Medium",
                "assigned_to": self.staff.id
            },
            format="json"
        )
        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(self.staff)

        response = self.client.post(
            f"/api/complaints/{cid}/reply/",
            {"body": "Please restart the router"},
            format="json"
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            f"/api/complaints/{cid}/review/",
            {
                "status": "Resolved",
                "category": "Technical Issue",
                "priority": "Medium"
            },
            format="json"
        )
        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(self.customer)

        response = self.client.get("/api/notifications/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"/api/complaints/{cid}/")
        self.assertEqual(response.data["status"], "Resolved")

    # TEST 2: Authentication and input validation
    def test_auth_and_validation(self):
        self.client.force_authenticate(None)

        response = self.client.get("/api/complaints/")
        self.assertEqual(response.status_code, 401)

        response = self.client.post(
            "/api/register/",
            {
                "username": "newuser",
                "password": "StrongPass945!",
                "email": "new@example.com"
            },
            format="json"
        )
        self.assertEqual(response.status_code, 201)

        self.client.credentials(
            HTTP_AUTHORIZATION="Token " + response.data["token"]
        )

        response = self.client.post(
            "/api/complaints/",
            {
                "title": "x",
                "description": "short"
            },
            format="json"
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post("/api/logout/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/api/me/")
        self.assertEqual(response.status_code, 401)

    # TEST 3: Staff department isolation
    def test_staff_department_isolation(self):
        complaint = Complaint.objects.create(
            user=self.customer,
            title="Invoice",
            description="Wrong payment invoice",
            category="Billing/Payment",
            priority="Medium",
            department="Accounts",
            sentiment="Neutral",
            confidence=0.6
        )

        self.client.force_authenticate(self.staff)

        response = self.client.get(
            f"/api/complaints/{complaint.id}/"
        )
        self.assertEqual(response.status_code, 404)

    # TEST 4: Editing, reanalysis and deletion history
    def test_edit_reanalyzes_and_delete_preserves_history(self):
        response = self.client.post(
            "/api/complaints/",
            {
                "title": "Internet issue",
                "description": "My wifi network connection is not working"
            },
            format="json"
        )

        cid = response.data["id"]

        response = self.client.patch(
            f"/api/complaints/{cid}/",
            {
                "title": "Payment problem",
                "description": "Payment deducted but subscription inactive"
            },
            format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"], "Billing/Payment")
        self.assertEqual(response.data["department"], "Accounts")
        self.assertTrue(response.data["can_edit"])
        self.assertEqual(len(response.data["history"]), 2)

        response = self.client.delete(
            f"/api/complaints/{cid}/"
        )
        self.assertEqual(response.status_code, 204)

        complaint = Complaint.objects.get(id=cid)
        self.assertTrue(complaint.is_archived)
        self.assertEqual(complaint.history.count(), 3)

        response = self.client.get(f"/api/complaints/{cid}/")
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/api/complaints/")
        self.assertEqual(response.data, [])

        response = self.client.get("/api/notifications/")
        self.assertEqual(response.data, [])

    # TEST 5: Edit and delete restrictions
    def test_edit_delete_restrictions(self):
        complaint = Complaint.objects.create(
            user=self.customer,
            title="Internet",
            description="Internet connection broken",
            category="Technical Issue",
            priority="Medium",
            department="IT Support",
            sentiment="Neutral",
            confidence=0.7
        )

        for user in [self.other, self.admin, self.staff]:
            self.client.force_authenticate(user)

            for method in [self.client.patch, self.client.delete]:
                response = method(
                    f"/api/complaints/{complaint.id}/",
                    {"title": "Changed"},
                    format="json"
                )
                self.assertIn(response.status_code, [403, 404])

        self.client.force_authenticate(self.customer)

        response = self.client.patch(
            f"/api/complaints/{complaint.id}/",
            {"description": "short"},
            format="json"
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.patch(
            f"/api/complaints/{complaint.id}/",
            {"status": "Resolved"},
            format="json"
        )
        self.assertEqual(response.status_code, 400)

        for status, assigned in [
            ("Assigned", None),
            ("Submitted", self.staff)
        ]:
            complaint.status = status
            complaint.assigned_to = assigned
            complaint.save()

            response = self.client.patch(
                f"/api/complaints/{complaint.id}/",
                {"title": "Changed"},
                format="json"
            )
            self.assertEqual(response.status_code, 403)

            response = self.client.delete(
                f"/api/complaints/{complaint.id}/"
            )
            self.assertEqual(response.status_code, 403)

    # TEST 6: File validation and private download
    def test_upload_validation_and_private_download(self):
        with tempfile.TemporaryDirectory() as folder:
            with override_settings(MEDIA_ROOT=folder):

                response = self.client.post(
                    "/api/complaints/",
                    {
                        "title": "Internet failure",
                        "description": "My wifi network connection is broken"
                    },
                    format="json"
                )
                self.assertEqual(response.status_code, 201)

                cid = response.data["id"]

                # Invalid PDF must be rejected
                response = self.client.post(
                    f"/api/complaints/{cid}/upload/",
                    {
                        "file": SimpleUploadedFile(
                            "bad.pdf",
                            b"not a pdf"
                        )
                    },
                    format="multipart"
                )
                self.assertEqual(response.status_code, 400)

                # Valid PDF must be accepted
                response = self.client.post(
                    f"/api/complaints/{cid}/upload/",
                    {
                        "file": SimpleUploadedFile(
                            "evidence.pdf",
                            b"%PDF-1.4\n%%EOF",
                            content_type="application/pdf"
                        )
                    },
                    format="multipart"
                )
                self.assertEqual(response.status_code, 201)

                attachment_id = response.data["id"]

                url = (
                    f"/api/complaints/{cid}/attachments/"
                    f"{attachment_id}/"
                )

                # Complaint owner can download
                download_response = self.client.get(url)

                try:
                    self.assertEqual(
                        download_response.status_code, 200
                    )

                    content = b"".join(
                        download_response.streaming_content
                    )

                    self.assertTrue(
                        content.startswith(b"%PDF")
                    )
                finally:
                    download_response.close()

                # Another customer cannot download
                self.client.force_authenticate(self.other)

                other_response = self.client.get(url)

                try:
                    self.assertEqual(
                        other_response.status_code, 404
                    )
                finally:
                    other_response.close()

    # TEST 7: Admin settings and department routing
    def test_admin_settings_and_routing(self):
        response = self.client.get("/api/configuration/")
        self.assertEqual(response.status_code, 403)

        self.client.force_authenticate(self.admin)

        response = self.client.post(
            "/api/configuration/",
            {
                "kind": "department",
                "name": "New IT",
                "active": True
            },
            format="json"
        )
        self.assertEqual(response.status_code, 200)

        department = next(
            dep
            for dep in response.data["departments"]
            if dep["name"] == "New IT"
        )

        response = self.client.post(
            "/api/configuration/",
            {
                "kind": "category",
                "name": "Technical Issue",
                "department": department["id"],
                "active": True
            },
            format="json"
        )
        self.assertEqual(response.status_code, 200)

        self.client.force_authenticate(self.customer)

        response = self.client.post(
            "/api/complaints/",
            {
                "title": "Network issue",
                "description": "My wifi network connection is not working"
            },
            format="json"
        )

        self.assertEqual(
            response.data["department"],
            "New IT"
        )
