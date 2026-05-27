from __future__ import annotations

import base64
import json
import logging
import time
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClerkUser:
    user_id: str
    email: str


class ClerkVerifier:
    def __init__(self, jwks_url: str, issuer: str):
        self.jwks_url = jwks_url
        self.issuer = issuer
        self._jwks: list[dict] | None = None
        self._cache_expiry: float = 0

    def _fetch_jwks(self) -> list[dict]:
        now = time.time()
        if self._jwks and now < self._cache_expiry:
            return self._jwks
        try:
            resp = urllib.request.urlopen(self.jwks_url, timeout=10)
            body = json.loads(resp.read().decode("utf-8"))
            self._jwks = body.get("keys", [])
            self._cache_expiry = now + 3600
            return self._jwks
        except Exception as exc:
            logger.warning("Failed to fetch Clerk JWKS: %s", exc)
            return self._jwks or []

    def verify(self, token: str) -> ClerkUser | None:
        try:
            header_b64, payload_b64, sig_b64 = token.split(".")
        except ValueError:
            return None
        try:
            header = json.loads(_b64_decode(header_b64))
            payload = json.loads(_b64_decode(payload_b64))
        except Exception:
            return None
        if payload.get("iss") != self.issuer:
            return None
        exp = payload.get("exp", 0)
        if exp < time.time():
            return None
        kid = header.get("kid", "")
        keys = self._fetch_jwks()
        matching = [k for k in keys if k.get("kid") == kid]
        if not matching:
            logger.warning("No matching Clerk JWK for kid=%s", kid)
            return None
        key_data = matching[0]
        n_bytes = _b64_decode(key_data.get("n", ""))
        e_bytes = _b64_decode(key_data.get("e", ""))
        if not _verify_rs256(f"{header_b64}.{payload_b64}", sig_b64, n_bytes, e_bytes):
            logger.warning("Clerk JWT signature verification failed")
            return None
        sub = payload.get("sub", "")
        email = payload.get("email", "") or ""
        return ClerkUser(user_id=sub, email=email)


def _b64_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded)


def _verify_rs256(signing_input: str, signature_b64: str, n_bytes: bytes, e_bytes: bytes) -> bool:
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa, padding
        from cryptography.hazmat.primitives import hashes
        e_int = int.from_bytes(e_bytes, "big")
        n_int = int.from_bytes(n_bytes, "big")
        public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
        signature = _b64_decode(signature_b64)
        public_key.verify(signature, signing_input.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False
