"""Unit tests for core/credentials.py — get_login_kwargs() env var lookup."""

from ojhunt.core.credentials import get_login_kwargs


def test_both_vars_set_returns_kwargs(monkeypatch):
    monkeypatch.setenv("LOGIN_USERNAME__FOO", "alice")
    monkeypatch.setenv("LOGIN_PASSWORD__FOO", "s3cr3t")

    result = get_login_kwargs("foo")

    assert result == {"login_user": "alice", "login_password": "s3cr3t"}


def test_only_username_returns_none(monkeypatch):
    monkeypatch.setenv("LOGIN_USERNAME__FOO", "alice")
    monkeypatch.delenv("LOGIN_PASSWORD__FOO", raising=False)

    assert get_login_kwargs("foo") is None


def test_neither_var_set_returns_none(monkeypatch):
    monkeypatch.delenv("LOGIN_USERNAME__FOO", raising=False)
    monkeypatch.delenv("LOGIN_PASSWORD__FOO", raising=False)

    assert get_login_kwargs("foo") is None
