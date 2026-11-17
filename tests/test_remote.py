"""Offline Access checks and isolated HTTP tests on port 8571."""

import base64
import hashlib
import http.client
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from email.message import Message
from unittest.mock import patch

from core.access import AccessUnavailable, AccessValidator, InvalidToken


# Throwaway 2048-bit key, generated once with Git's openssl genrsa (test use only).
N = int(
    "d8d35283f76c104a4465817356ddf983859891439fce58a7303bdcd3d5bd651e481ffb1427cf5fcf"
    "f5c644d30312d5f40c8d7b53e81474bec561b9f94a931096094e37e3e31e460baff6f590f4b440bf"
    "e33ee717001ac3ec7676547782542bfd634f7e07d25c96cf1ffc5ec98004dc58fb91dec545a47f319c"
    "da7c7b8b84ec474941dee1d9bdd3ac2cf2ed743ff9b7731261a1acdb0fc7614fd09208e829f2f005"
    "1b92d23e7374172ac53946756ea2854872869f432d76b2e9af71e6c4453a7b7ceba7feb5b5859b"
    "7dbd5eac3b3c4b63723f5a81292ac50b5f77b11c01cc6351f7dd358097148e341c94694b9ef215"
    "f0766582814521b3a96ad9f8cf4453f29d", 16)
E = 65537
D = int(
    "02e39bf59cb220ac70a95e9674199c95c34db35fd08d0e12da3a6df897a040acecde9a389c482f"
    "d96447ba4a8a7fb180a13b3061bf95a831938d380e698f38991b3222de033c77c7f7960593232394"
    "ba49d3a07e26b6f495ddc5395e674aea5423c2df25c908894ce4baf6e35df492a00fe8136d12febc"
    "60239c28acf7c0b36a4078d817014bbc42a6ff6f1965d43589c62541cc74f614063741f56800a65c"
    "34cc32ad219d4f0ddd283b93cda84353f9b53689e0d4f2cd99811c42ae016123421f6c362e7dc3"
    "42e550c4a88d205f9af7722b49df01e10b9f0178b3d1ff86204949651ff9499c65db8900b42dce"
    "04a32d1fd8f6d8155da279592aa0f0d59c7641", 16)
HOST = "person.example.com"
TEAM = "example-team"
AUD = "test-audience"
ROOT = Path(__file__).resolve().parents[1]


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def number(value):
    return b64(value.to_bytes((value.bit_length() + 7) // 8, "big"))


CERTS = {"keys": [{"kid": "test-key", "n": number(N), "e": number(E)}]}


def token(header=None, **claims):
    head = b64(json.dumps(header or {"alg": "RS256", "kid": "test-key"}).encode())
    payload = {"iss": "https://example-team.cloudflareaccess.com", "aud": [AUD],
               "exp": time.time() + 300, "email": "tester@example.invalid"}
    payload.update(claims)
    body = b64(json.dumps(payload).encode())
    digest = bytes.fromhex("3031300d060960864801650304020105000420")
    digest += hashlib.sha256((head + "." + body).encode()).digest()
    k = (N.bit_length() + 7) // 8
    em = b"\x00\x01" + b"\xff" * (k - len(digest) - 3) + b"\x00" + digest
    sig = pow(int.from_bytes(em, "big"), D, N).to_bytes(k, "big")
    return head + "." + body + "." + b64(sig)


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.validator = AccessValidator(TEAM, AUD)
        fetch = patch.object(self.validator, "_fetch_certs", return_value=CERTS)
        self.fetch = fetch.start()
        self.addCleanup(fetch.stop)

    def test_valid_token_and_string_audience(self):
        for aud in ([AUD], AUD):
            self.assertEqual(self.validator.validate(token(aud=aud)), "tester@example.invalid")

    def test_invalid_tokens(self):
        good = token()
        cases = {
            "wrong aud": token(aud="other"), "wrong iss": token(iss="https://other.invalid"),
            "expired": token(exp=time.time() - 61), "future nbf": token(nbf=time.time() + 120),
            "bad signature": good.rsplit(".", 1)[0] + "." + b64(bytes(256)),
            "short signature": good.rsplit(".", 1)[0] + ".AA",
            "signature >= modulus": good.rsplit(".", 1)[0] + "." + number(N),
            "none": token({"alg": "none", "kid": "test-key"}),
            "HS256": token({"alg": "HS256", "kid": "test-key"}),
            "unknown kid": token({"alg": "RS256", "kid": "unknown"}),
            "missing kid": token({"alg": "RS256"}), "malformed": "bad.token",
            "bad base64": "!.e30.AA", "empty": "", "nan exp": token(exp=float("nan")),
            "nonobject header": "W10.e30.AA", "nonobject claims": "e30.W10.AA",
        }
        for name, value in cases.items():
            with self.subTest(name=name), self.assertRaises(InvalidToken):
                self.validator.validate(value)

    def test_clock_leeway(self):
        self.validator.validate(token(exp=time.time() - 30, nbf=time.time() + 30))

    def test_cache_and_unknown_kid_refresh(self):
        with patch("core.access.time.monotonic", return_value=100):
            self.validator.validate(token())
        unknown = token({"alg": "RS256", "kid": "new"})
        with patch("core.access.time.monotonic", return_value=159):
            with self.assertRaises(InvalidToken):
                self.validator.validate(unknown)
        self.assertEqual(self.fetch.call_count, 1)
        with patch("core.access.time.monotonic", return_value=160):
            with self.assertRaises(InvalidToken):
                self.validator.validate(unknown)
            with self.assertRaises(InvalidToken):
                self.validator.validate(unknown)
        self.assertEqual(self.fetch.call_count, 2)
        with patch("core.access.time.monotonic", return_value=3761):
            self.validator.validate(token())
        self.assertEqual(self.fetch.call_count, 3)

    def test_rotation_and_thread_safety(self):
        signed = token()
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(list(pool.map(self.validator.validate, [signed] * 16)),
                             ["tester@example.invalid"] * 16)
        self.assertEqual(self.fetch.call_count, 1)
        self.validator._last_fetch -= 60
        self.fetch.return_value = {"keys": [dict(CERTS["keys"][0], kid="new")]}
        self.validator.validate(token({"alg": "RS256", "kid": "new"}))

    def test_cert_failure_is_unavailable_and_throttled(self):
        self.fetch.side_effect = OSError("offline")
        for _ in range(2):
            with self.assertRaises(AccessUnavailable):
                self.validator.validate(token())
        self.assertEqual(self.fetch.call_count, 1)

    def test_cert_url_and_timeout(self):
        validator = AccessValidator(TEAM, AUD)
        with patch("core.access.urllib.request.urlopen") as request:
            request.return_value.__enter__.return_value.read.return_value = json.dumps(CERTS).encode()
            validator.validate(token())
        request.assert_called_once_with(
            "https://example-team.cloudflareaccess.com/cdn-cgi/access/certs", timeout=5)


class RemoteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="pai-remote-tests-")
        # Start empty; tests must never read or migrate the user's legacy database.
        (Path(cls.temp.name) / "person_ai.db").touch()
        cls.env = patch.dict(os.environ, {"PAI_FAKE": "1", "PAI_PORT": "8571",
                            "PAI_DATA_DIR": cls.temp.name, "PAI_PUBLIC_HOST": "",
                            "PAI_ACCESS_TEAM": "", "PAI_ACCESS_AUD": ""})
        cls.env.start()
        cls.server = importlib.import_module("server")
        cls.httpd = cls.server.ThreadingHTTPServer(("127.0.0.1", 8571), cls.server.Handler)
        cls.httpd.allow_lan = False
        cls.httpd.daemon_threads = True
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.username = "remote_test_" + os.urandom(6).hex()
        user = cls.server.db.create_user(cls.username, "test-password")
        cls.user_id = user["id"]

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()
        cls.server.db.conn.close()
        cls.env.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.cookie = self.server.COOKIE + "=" + self.server.db.create_auth_session(self.user_id)
        for name, value in (("PAI_PUBLIC_HOST", HOST), ("PAI_ACCESS_TEAM", TEAM), ("PAI_ACCESS_AUD", AUD)):
            p = patch.object(self.server.config, name, value)
            p.start()
            self.addCleanup(p.stop)
        validator = AccessValidator(TEAM, AUD)
        p = patch.object(self.server, "access", validator)
        p.start()
        self.addCleanup(p.stop)
        p = patch.object(validator, "_fetch_certs", return_value=CERTS)
        self.fetch = p.start()
        self.addCleanup(p.stop)
        p = patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden"))
        p.start()
        self.addCleanup(p.stop)

    def request(self, path, method="GET", headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", 8571, timeout=5)
        try:
            conn.request(method, path, body=json.dumps(body) if body is not None else None,
                         headers=headers if headers is not None else {"Host": HOST})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def tunnel_headers(self):
        return {"Host": HOST, "Cf-Access-Jwt-Assertion": token(), "Cookie": self.cookie,
                "Cf-Connecting-Ip": "203.0.113.7"}

    def handler(self, host="127.0.0.1", **headers):
        handler = object.__new__(self.server.Handler)
        handler.client_address = ("127.0.0.1", 1234)
        handler.headers = Message()
        handler.headers["Host"] = host
        for name, value in headers.items():
            handler.headers[name] = value
        return handler

    def test_request_classification(self):
        self.assertFalse(self.handler(HOST)._from_this_computer())
        self.assertFalse(self.handler(**{"Cf-Ray": ""})._from_this_computer())
        self.assertTrue(self.handler()._from_this_computer())
        self.assertTrue(self.handler("LOCALHOST:8571")._from_this_computer())
        self.assertTrue(self.handler("[::1]:8571")._from_this_computer())
        self.assertFalse(self.handler("evil.invalid")._from_this_computer())
        self.assertTrue(self.handler(HOST.upper() + ":443")._via_tunnel())
        for name in ("Cf-Ray", "Cf-Visitor", "Cf-Connecting-Ip", "Cf-Access-Jwt-Assertion"):
            self.assertTrue(self.handler(**{name: ""})._via_tunnel())

    def test_missing_or_invalid_token_blocks_static_and_api(self):
        for path in ("/", "/api/auth/me"):
            for headers in ({"Host": HOST}, {"Host": HOST, "Cf-Access-Jwt-Assertion": "bad"},
                            {"Host": "127.0.0.1", "Cf-Ray": "test"}):
                with self.subTest(path=path, headers=list(headers)):
                    self.assertEqual(self.request(path, headers=headers)[0], 403)

    def test_valid_tunnel_and_privileged_operations(self):
        headers = self.tunnel_headers()
        status, _, body = self.request("/api/auth/me", headers=headers)
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(body)["local"])
        self.assertEqual(self.request("/", headers=headers)[0], 200)
        status, _, body = self.request("/api/auth/reset", "POST", headers,
                                       {"username": self.username, "password": "new-password"})
        self.assertEqual((status, json.loads(body)["error"]), (403, "reset_local_only"))
        status, _, body = self.request("/api/keys/groq", "PUT", headers, {"key": "unused"})
        self.assertEqual((status, json.loads(body)["error"]), (403, "keys_local_only"))

    def test_cert_failure_returns_503(self):
        self.fetch.side_effect = OSError("offline")
        for path in ("/", "/api/auth/me"):
            self.assertEqual(self.request(path, headers=self.tunnel_headers())[0], 503)

    def test_cookie_secure_only_for_tunnel(self):
        for headers, secure in ((self.tunnel_headers(), True), ({"Host": "127.0.0.1"}, False)):
            status, response_headers, _ = self.request("/api/auth/logout", "POST", headers, {})
            self.assertEqual(status, 200)
            self.assertEqual("; Secure" in response_headers["Set-Cookie"], secure)

    def test_client_ip_requires_validated_tunnel(self):
        handler = self.handler(HOST, **{"Cf-Connecting-Ip": "2001:db8::1"})
        self.assertEqual(handler._client_ip(), "127.0.0.1")
        handler._access_validated = True
        self.assertEqual(handler._client_ip(), "2001:db8::1")
        handler.headers.replace_header("Cf-Connecting-Ip", "invalid")
        self.assertEqual(handler._client_ip(), "127.0.0.1")

    def test_rate_limits_use_tunnel_ip(self):
        with patch.object(self.server, "rate_limited", return_value=False) as limited:
            with patch.object(self.server, "note_failure") as failure:
                self.request("/api/auth/login", "POST", self.tunnel_headers(),
                             {"username": self.username, "password": "wrong-password"})
                limited.assert_called_once_with("login|203.0.113.7")
                failure.assert_called_once_with("login|203.0.113.7")
                failure.reset_mock()
                self.request("/api/account/password", "POST", self.tunnel_headers(),
                             {"current": "wrong-password", "password": "new-password"})
                failure.assert_called_once_with("password|203.0.113.7")

    def test_remote_off_preserves_local_access(self):
        with patch.object(self.server.config, "PAI_PUBLIC_HOST", ""):
            headers = {"Host": "127.0.0.1:8571", "Cookie": self.cookie}
            status, _, body = self.request("/api/auth/me", headers=headers)
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(body)["local"])
            self.assertEqual(self.request("/", headers=headers)[0], 200)
            self.assertEqual(self.request("/api/auth/me", headers={"Host": HOST})[0], 403)
            # Exercise the real local reset/key guards without changing stored credentials.
            with patch.object(self.server.db, "find_user", return_value=None):
                status, _, body = self.request("/api/auth/reset", "POST", headers,
                                               {"username": self.username, "password": "password"})
                self.assertEqual((status, json.loads(body)["error"]), (404, "no_such_user"))
            with patch.object(self.server.config, "set_key") as save:
                with patch.object(self.server, "resolve_model"), \
                        patch.object(self.server.config, "key_status", return_value={}), \
                        patch.object(self.server.config, "models_payload", return_value=[]):
                    self.assertEqual(self.request("/api/keys/groq", "PUT", headers, {"key": "test"})[0], 200)
                save.assert_called_once_with("groq", "test")

    def test_lan_rules_preserved(self):
        handler = self.handler("192.168.1.2:8571")
        handler.client_address = ("192.168.1.3", 1234)
        handler.server = type("Server", (), {"allow_lan": True})()
        handler.connection = type("Connection", (), {"getsockname": lambda s: ("192.168.1.2", 8571)})()
        handler._error = lambda *args: None
        self.assertTrue(handler._local_only())
        self.assertFalse(handler._from_this_computer())
        handler.client_address = ("8.8.8.8", 1234)
        self.assertFalse(handler._local_only())

    def test_startup_requires_team_and_audience(self):
        for team, aud in (("", ""), (TEAM, ""), ("", AUD)):
            with self.subTest(team=team, aud=aud), tempfile.TemporaryDirectory(prefix="pai-startup-") as data:
                env = dict(os.environ, PAI_DATA_DIR=data, PAI_PUBLIC_HOST=HOST,
                           PAI_ACCESS_TEAM=team, PAI_ACCESS_AUD=aud, PAI_PORT="8571", PAI_FAKE="1")
                result = subprocess.run([sys.executable, "server.py", "--no-browser"], cwd=ROOT,
                                        env=env, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("PAI_ACCESS_TEAM ve PAI_ACCESS_AUD gerekli", result.stderr)


if __name__ == "__main__":
    unittest.main()
