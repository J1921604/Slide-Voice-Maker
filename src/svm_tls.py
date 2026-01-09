"""TLS/証明書の共通設定。

背景:
  Edge TTS(edge-tts) は内部で aiohttp を使い https 接続します。
  社内プロキシの SSL インスペクション等で証明書チェーンに自己署名が混ざると、
  Python 側で `CERTIFICATE_VERIFY_FAILED` になりやすいです。

方針:
  - デフォルトは安全側（検証ON）
  - Windows では可能なら OS 証明書ストアを使う (truststore)
  - 追加のCAが必要なら PEM バンドルを指定できる
  - どうしても…の最終手段として、明示的な環境変数時だけ検証OFF

環境変数:
  - SVM_USE_TRUSTSTORE=1|0
      1: truststore を利用して OS 証明書ストアを使う（推奨, 既定=1）
  - SVM_SSL_CERT_FILE=<path-to-ca-bundle.pem>
      OpenSSL の検証で使うCAバンドルを明示
  - SVM_SSL_CERT_DIR=<path-to-ca-dir>
      OpenSSL の検証で使うCAディレクトリを明示
  - SVM_TLS_INSECURE=1
      最終手段: SSL検証を無効化（危険。社内ネットワーク等での一時対応用）
  - SVM_HTTPS_PROXY / HTTPS_PROXY / https_proxy
      プロキシ指定（edge-tts が proxy 引数を受ける場合のみ利用）
"""

from __future__ import annotations

import contextlib
import os
import ssl
from dataclasses import dataclass
from typing import Iterator, Optional


@dataclass(frozen=True)
class TlsConfigResult:
    used_truststore: bool
    ssl_cert_file: Optional[str]
    ssl_cert_dir: Optional[str]


_CONFIGURED = False


def _truthy(v: Optional[str]) -> bool:
    if v is None:
        return False
    return v.strip().lower() in {"1", "true", "yes", "on"}


def configure_outbound_tls() -> TlsConfigResult:
    """外向きHTTPS通信のためのTLS設定を一度だけ適用する。"""
    global _CONFIGURED
    if _CONFIGURED:
        return TlsConfigResult(
            used_truststore=False,
            ssl_cert_file=os.environ.get("SSL_CERT_FILE"),
            ssl_cert_dir=os.environ.get("SSL_CERT_DIR"),
        )

    used_truststore = False

    # 1) OS証明書ストアを使う（Windowsで特に有効）
    #    truststore が無い/失敗した場合はフォールバック。
    if os.environ.get("SVM_USE_TRUSTSTORE") is None or _truthy(os.environ.get("SVM_USE_TRUSTSTORE")):
        try:
            import truststore  # type: ignore

            truststore.inject_into_ssl()
            used_truststore = True
        except Exception:
            # truststore が無い/使えない環境は無視して続行
            used_truststore = False

    # 2) 明示CA（SVM_* を優先して SSL_CERT_* に反映）
    svm_cert_file = os.environ.get("SVM_SSL_CERT_FILE")
    if svm_cert_file:
        os.environ["SSL_CERT_FILE"] = svm_cert_file

    svm_cert_dir = os.environ.get("SVM_SSL_CERT_DIR")
    if svm_cert_dir:
        os.environ["SSL_CERT_DIR"] = svm_cert_dir

    _CONFIGURED = True
    return TlsConfigResult(
        used_truststore=used_truststore,
        ssl_cert_file=os.environ.get("SSL_CERT_FILE"),
        ssl_cert_dir=os.environ.get("SSL_CERT_DIR"),
    )


def get_https_proxy_from_env() -> Optional[str]:
    # SVM_ を優先し、一般的な環境変数にもフォールバック
    for key in ("SVM_HTTPS_PROXY", "HTTPS_PROXY", "https_proxy"):
        v = os.environ.get(key)
        if v and v.strip():
            return v.strip()
    return None


@contextlib.contextmanager
def insecure_tls_if_enabled() -> Iterator[None]:
    """SVM_TLS_INSECURE=1 のときだけ SSL 検証を無効化する（最終手段）。"""
    if not _truthy(os.environ.get("SVM_TLS_INSECURE")):
        yield
        return

    orig_create_default_context = ssl.create_default_context

    def _insecure_create_default_context(*args, **kwargs):
        # aiohttp はここで作られる context を使うことが多い
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    ssl.create_default_context = _insecure_create_default_context  # type: ignore[assignment]
    try:
        yield
    finally:
        ssl.create_default_context = orig_create_default_context  # type: ignore[assignment]
