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


def test_vjudge_backwards_compat(monkeypatch):
    monkeypatch.delenv("LOGIN_USERNAME__VJUDGE", raising=False)
    monkeypatch.delenv("LOGIN_PASSWORD__VJUDGE", raising=False)
    monkeypatch.setenv("VJUDGE_USERNAME", "vjuser")
    monkeypatch.setenv("VJUDGE_PASSWORD", "vjpass")

    result = get_login_kwargs("vjudge")

    assert result == {"login_user": "vjuser", "login_password": "vjpass"}


def test_vjudge_new_style_takes_precedence(monkeypatch):
    monkeypatch.setenv("LOGIN_USERNAME__VJUDGE", "new_user")
    monkeypatch.setenv("LOGIN_PASSWORD__VJUDGE", "new_pass")
    monkeypatch.setenv("VJUDGE_USERNAME", "old_user")
    monkeypatch.setenv("VJUDGE_PASSWORD", "old_pass")

    result = get_login_kwargs("vjudge")

    assert result == {"login_user": "new_user", "login_password": "new_pass"}


def test_vjudge_backwards_compat_does_not_apply_to_other_crawlers(monkeypatch):
    monkeypatch.delenv("LOGIN_USERNAME__CODEFORCES", raising=False)
    monkeypatch.delenv("LOGIN_PASSWORD__CODEFORCES", raising=False)
    monkeypatch.setenv("VJUDGE_USERNAME", "vjuser")
    monkeypatch.setenv("VJUDGE_PASSWORD", "vjpass")

    assert get_login_kwargs("codeforces") is None
