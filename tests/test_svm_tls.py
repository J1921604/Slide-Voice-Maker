from __future__ import annotations

import importlib
import ssl

import pytest


def test_configure_outbound_tls_sets_ssl_cert_file(monkeypatch: pytest.MonkeyPatch):
    # 過去の設定が残っていてもテストが独立するように環境を掃除
    monkeypatch.delenv("SVM_SSL_CERT_FILE", raising=False)
    monkeypatch.delenv("SSL_CERT_FILE", raising=False)

    # truststore は環境により有無があるため無効化して影響を排除
    monkeypatch.setenv("SVM_USE_TRUSTSTORE", "0")

    import svm_tls
    importlib.reload(svm_tls)  # モジュール内キャッシュ(_CONFIGURED)をリセット

    monkeypatch.setenv("SVM_SSL_CERT_FILE", r"C:\dummy\corp.pem")
    r = svm_tls.configure_outbound_tls()
    # OpenSSLのデフォルトCA(cafile)は環境により None のことがあるため、そこは前提にしない。
    assert r.ssl_cert_file == r"C:\dummy\corp.pem"
    assert svm_tls.os.environ.get("SSL_CERT_FILE") == r"C:\dummy\corp.pem"


def test_insecure_tls_if_enabled_patches_create_default_context(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SVM_TLS_INSECURE", "1")

    from svm_tls import insecure_tls_if_enabled

    orig = ssl.create_default_context
    with insecure_tls_if_enabled():
        ctx = ssl.create_default_context()
        assert ctx.verify_mode == ssl.CERT_NONE
        assert ctx.check_hostname is False

    # 後始末されていること
    assert ssl.create_default_context is orig
