"""Cloudflare Access JWT checks (standard library only)."""

import base64
import binascii
import hashlib
import hmac
import json
import math
import re
import threading
import time
import urllib.request


class InvalidToken(ValueError):
    pass


class AccessUnavailable(Exception):
    pass


def _decode(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise InvalidToken("invalid token")
    try:
        return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
    except (ValueError, binascii.Error):
        raise InvalidToken("invalid token") from None


class AccessValidator:
    def __init__(self, team, audience):
        self.issuer = "https://" + team + ".cloudflareaccess.com"
        self.audience = audience
        self._lock = threading.Lock()
        self._keys = {}
        self._expires = 0.0
        self._last_fetch = float("-inf")
        self._fetch_failed = False

    def _fetch_certs(self):
        with urllib.request.urlopen(self.issuer + "/cdn-cgi/access/certs", timeout=5) as response:
            return json.loads(response.read())

    def _key(self, kid):
        with self._lock:
            now = time.monotonic()
            if now >= self._expires or kid not in self._keys:
                if now - self._last_fetch >= 60:
                    self._last_fetch = now
                    try:
                        keys = {}
                        for jwk in self._fetch_certs()["keys"]:
                            n = int.from_bytes(_decode(jwk["n"]), "big")
                            e = int.from_bytes(_decode(jwk["e"]), "big")
                            if not isinstance(jwk["kid"], str) or n <= 0 or e < 3 or e % 2 == 0:
                                raise ValueError("invalid key")
                            keys[jwk["kid"]] = (n, e)
                        if not keys:
                            raise ValueError("no keys")
                    except Exception:
                        self._fetch_failed = True
                        raise AccessUnavailable() from None
                    self._keys = keys
                    self._expires = now + 3600
                    self._fetch_failed = False
                elif self._fetch_failed or now >= self._expires:
                    raise AccessUnavailable()
            if kid not in self._keys:
                raise InvalidToken("invalid token")
            return self._keys[kid]

    def validate(self, token):
        """Return the email, or reject without exposing token contents."""
        try:
            head, body, sig = token.split(".")
            header = json.loads(_decode(head))
            claims = json.loads(_decode(body))
            signature = _decode(sig)
            if not isinstance(header, dict) or not isinstance(claims, dict):
                raise InvalidToken("invalid token")
            kid = header.get("kid")
            if header.get("alg") != "RS256" or not isinstance(kid, str) or not kid:
                raise InvalidToken("invalid token")
            aud = claims.get("aud")
            if isinstance(aud, str):
                aud = [aud]
            now = time.time()
            exp, nbf = claims.get("exp"), claims.get("nbf", now)
            if (claims.get("iss") != self.issuer or not isinstance(aud, list)
                    or self.audience not in aud
                    or type(exp) not in (int, float) or not math.isfinite(exp)
                    or type(nbf) not in (int, float) or not math.isfinite(nbf)
                    or exp <= now - 60 or nbf > now + 60
                    or not isinstance(claims.get("email"), str) or not claims["email"]):
                raise InvalidToken("invalid token")
            n, e = self._key(kid)
            k = (n.bit_length() + 7) // 8
            s = int.from_bytes(signature, "big")
            if len(signature) != k or s >= n:
                raise InvalidToken("invalid token")
            digest = bytes.fromhex("3031300d060960864801650304020105000420")
            digest += hashlib.sha256((head + "." + body).encode("ascii")).digest()
            padding = k - len(digest) - 3
            if padding < 8:
                raise InvalidToken("invalid token")
            expected = b"\x00\x01" + b"\xff" * padding + b"\x00" + digest
            if not hmac.compare_digest(pow(s, e, n).to_bytes(k, "big"), expected):
                raise InvalidToken("invalid token")
            return claims["email"]
        except (ValueError, TypeError, AttributeError, KeyError, OverflowError, RecursionError):
            raise InvalidToken("invalid token") from None
