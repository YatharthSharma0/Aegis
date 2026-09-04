"""Argon2 password hashing."""

from app.security.passwords import hash_password, needs_rehash, verify_password


def test_hash_is_not_the_plaintext_and_verifies():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2")
    assert verify_password("correct horse battery staple", hashed)


def test_wrong_password_does_not_verify():
    assert not verify_password("nope", hash_password("secret-value"))


def test_garbage_hash_does_not_raise():
    assert not verify_password("x", "not-a-hash")


def test_current_hash_does_not_need_rehash():
    assert not needs_rehash(hash_password("whatever"))
