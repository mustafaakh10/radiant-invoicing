import base64
import json
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from . import ai
from .models import AICall, AIConfig, Record, Upload

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


@override_settings(MEDIA_ROOT="/tmp/rl-test-media")
class ApiTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("owner", password="a-long-password-1")
        self.client.login(username="owner", password="a-long-password-1")

    def post(self, url, data):
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def test_needs_login(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/records").status_code, 401)
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_write_read_delete(self):
        r = self.post("/api/write", {"writes": [["products/p1", {"name": "Trail", "price": 4850}], ["settings/main", {"company": "RL"}]]})
        self.assertEqual(r.status_code, 200)
        rev1 = r.json()["rev"]
        data = self.client.get("/api/records").json()
        self.assertEqual(data["records"]["products/p1"]["price"], 4850)
        self.assertEqual(data["rev"], rev1)
        self.post("/api/write", {"writes": [["products/p1", None]]})
        self.assertNotIn("products/p1", self.client.get("/api/records").json()["records"])
        self.assertGreater(self.client.get("/api/rev").json()["rev"], rev1)

    def test_bad_paths_rejected(self):
        for p in ["../etc", "products", "a//b", "x/" + "y" * 200]:
            self.assertEqual(self.post("/api/write", {"writes": [[p, {}]]}).status_code, 400, p)
        self.assertEqual(Record.objects.count(), 0)

    def test_upload_image_only(self):
        r = self.client.post("/api/upload", {"file": SimpleUploadedFile("a.png", PNG, "image/png")})
        self.assertEqual(r.status_code, 200)
        url = r.json()["url"]
        self.assertTrue(url.startswith("/media/uploads/"))
        self.assertEqual(self.client.get(url).status_code, 200)
        bad = self.client.post("/api/upload", {"file": SimpleUploadedFile("a.html", b"<script>", "text/html")})
        self.assertEqual(bad.status_code, 400)

    def test_ai_key_never_returned(self):
        r = self.post("/api/ai/config", {"provider": "openai", "key": "sk-secret-123456789"})
        self.assertNotIn("sk-secret", json.dumps(r.json()))
        self.assertEqual(r.json()["keyHint"], "…6789")
        self.assertTrue(r.json()["ready"])

    @mock.patch("billing.ai._post")
    def test_ai_complete_logs_tokens_and_caches(self, post):
        post.return_value = (200, {"choices": [{"message": {"content": '{"i":[]}'}}], "usage": {"prompt_tokens": 120, "completion_tokens": 8}})
        self.post("/api/ai/config", {"provider": "openai", "key": "sk-x-123456789"})
        r1 = self.post("/api/ai/complete", {"prompt": "hello", "maxTokens": 50}).json()
        r2 = self.post("/api/ai/complete", {"prompt": "hello", "maxTokens": 50}).json()
        self.assertFalse(r1["cached"])
        self.assertTrue(r2["cached"])
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args[0][2]["max_tokens"], 50)
        u = self.client.get("/api/ai/usage").json()["month"]
        self.assertEqual((u["calls"], u["cached"], u["input"], u["output"]), (1, 1, 120, 8))

    @mock.patch("billing.ai._post")
    def test_ai_monthly_limit(self, post):
        post.return_value = (200, {"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 90, "completion_tokens": 20}})
        self.post("/api/ai/config", {"provider": "groq", "key": "gsk-123456789", "limit": 100})
        self.assertEqual(self.post("/api/ai/complete", {"prompt": "a"}).status_code, 200)
        r = self.post("/api/ai/complete", {"prompt": "b"})
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.json()["code"], "limit")

    @mock.patch("billing.ai._post")
    def test_ai_bad_key_message(self, post):
        post.return_value = (401, {"error": "nope"})
        self.post("/api/ai/config", {"provider": "anthropic", "key": "sk-ant-123456789"})
        r = self.post("/api/ai/complete", {"prompt": "x"})
        self.assertEqual(r.json()["code"], "bad_key")
        self.assertFalse(AICall.objects.get().ok)

    def test_import_rewrites_photo_refs(self):
        backup = {"app": "radiant-billing", "records": {
            "products/p1": {"name": "Trail", "img": "rl:abc"},
            "products/p2": {"name": "COB", "img": "/_blob/def"},
            "meta/seeded": {"at": 1}},
            "blobs": {"abc": {"type": "image/png", "b64": base64.b64encode(PNG).decode()},
                      "def": {"type": "image/png", "b64": base64.b64encode(PNG).decode()}}}
        r = self.post("/api/restore", backup).json()
        self.assertEqual(r, {"records": 2, "photos": 2})
        recs = self.client.get("/api/records").json()["records"]
        self.assertTrue(recs["products/p1"]["img"].startswith("/media/uploads/"))
        self.assertTrue(recs["products/p2"]["img"].startswith("/media/uploads/"))
        self.assertEqual(Upload.objects.count(), 2)
        # round trip through the server's own backup
        again = self.client.get("/api/backup").json()
        self.assertEqual(self.post("/api/restore", again).json()["records"], 2)
