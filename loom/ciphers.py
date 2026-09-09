import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets

import bcrypt
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import (
    AEADDecryptionContext,
    AEADEncryptionContext,
    Cipher,
    algorithms,
    modes,
)

IV_LEN = 12
TAG_LEN = 16
KEY_LEN = 32
ENCODED_KEY_LEN = len(base64.urlsafe_b64encode(b"\x00" * KEY_LEN))

MAX_PREFIX_LEN = 20
PREFIX_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")

PEPPER_ENV_VAR = "KEY_PEPPER"

DATA = list[dict] | dict | str


class CryptoError(Exception):
    pass


class InvalidKeyError(CryptoError):
    pass


class DecryptionError(CryptoError):
    pass


class MissingPepperError(CryptoError):
    pass


def _validate_prefix(prefix: str) -> None:
    if not isinstance(prefix, str) or not prefix:
        raise ValueError("prefix must be a non-empty string")

    if len(prefix) > MAX_PREFIX_LEN:
        raise ValueError(f"prefix must be at most {MAX_PREFIX_LEN} characters")

    if not PREFIX_RE.fullmatch(prefix):
        raise ValueError(
            "Prefix may only contain letters, digits & hyphens, and must start with a letter or digit."
        )


def get_key_prefix(key: str) -> str | None:
    if len(key) <= ENCODED_KEY_LEN:
        return None

    head = key[:-ENCODED_KEY_LEN]
    return head[:-1] if head.endswith("_") else None


def _decode_key(key: str) -> bytes:
    if not isinstance(key, str) or len(key) < ENCODED_KEY_LEN:
        raise InvalidKeyError("Invalid key: too short to be valid")

    payload = key[-ENCODED_KEY_LEN:]

    try:
        bkey = base64.urlsafe_b64decode(payload)

    except (binascii.Error, ValueError) as exc:
        raise InvalidKeyError("Invalid key: not valid base64") from exc

    if len(bkey) != KEY_LEN:
        raise InvalidKeyError(
            f"Invalid key length: expected {KEY_LEN} bytes, got {len(bkey)}"
        )

    return bkey


def _get_encryptor(key: str, iv: bytes) -> AEADEncryptionContext:
    bkey = _decode_key(key)
    return Cipher(
        algorithms.AES256(bkey),
        modes.GCM(iv),
        backend=default_backend(),
    ).encryptor()


def _get_decryptor(key: str, iv: bytes, tag: bytes) -> AEADDecryptionContext:
    bkey = _decode_key(key)
    return Cipher(
        algorithms.AES256(bkey),
        modes.GCM(iv, tag),
        backend=default_backend(),
    ).decryptor()


def generate_key(prefix: str | None = None) -> str:
    payload = base64.urlsafe_b64encode(secrets.token_bytes(KEY_LEN)).decode(
        "utf-8"
    )

    if prefix is None:
        return payload

    _validate_prefix(prefix)
    return f"{prefix}_{payload}"


def _resolve_pepper(pepper: str | bytes | None) -> bytes:
    if pepper is None:
        pepper = os.environ.get(PEPPER_ENV_VAR)

    if not pepper:
        raise MissingPepperError(
            f"No pepper provided and {PEPPER_ENV_VAR} is not set"
        )

    return pepper.encode("utf-8") if isinstance(pepper, str) else pepper


def _apply_pepper(key: str, pepper: bytes) -> bytes:
    digest = hmac.new(pepper, key.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest)


def hash_key(key: str, pepper: str | bytes | None = None) -> str:
    peppered = _apply_pepper(key, _resolve_pepper(pepper))
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(peppered, salt).decode("utf-8")


def verify_key(
    key: str, hashed_key: str, pepper: str | bytes | None = None
) -> bool:
    peppered = _apply_pepper(key, _resolve_pepper(pepper))
    return bcrypt.checkpw(peppered, hashed_key.encode("utf-8"))


def encrypt(data: DATA, key: str) -> bytes:
    iv = secrets.token_bytes(IV_LEN)
    encryptor = _get_encryptor(key, iv)

    json_data = json.dumps(data).encode("utf-8")
    ciphertext = encryptor.update(json_data) + encryptor.finalize()

    return base64.b64encode(iv + encryptor.tag + ciphertext)


def decrypt(encrypted_data: bytes, key: str) -> DATA:
    try:
        raw = base64.b64decode(encrypted_data, validate=True)

    except (binascii.Error, ValueError) as exc:
        raise DecryptionError("Encrypted data is not valid base64") from exc

    if len(raw) < IV_LEN + TAG_LEN:
        raise DecryptionError("Encrypted data is too short to be valid")

    iv = raw[:IV_LEN]
    tag = raw[IV_LEN : IV_LEN + TAG_LEN]
    ciphertext = raw[IV_LEN + TAG_LEN :]

    decryptor = _get_decryptor(key, iv, tag)

    try:
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()

    except InvalidTag as exc:
        raise DecryptionError(
            "Decryption failed: wrong key, or data is corrupted/tampered with"
        ) from exc

    try:
        return json.loads(decrypted_data.decode("utf-8"))

    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DecryptionError("Decrypted data is not valid JSON") from exc
