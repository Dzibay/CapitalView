"""
gRPC/TLS roots for T-Bank Invest API.

T-Bank uses certificates issued under Russian Trusted CA (Минцифры),
which are not in Mozilla/certifi or default gRPC roots — without them
Client() fails with CERTIFICATE_VERIFY_FAILED / self-signed in chain.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import certifi

# .../backend/app/infrastructure/external/brokers/tinkoff/ssl_support.py → backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[5]
_CERTS_DIR = _BACKEND_ROOT / "certs"


def _russian_trusted_pem_paths() -> list[Path]:
    return [
        _CERTS_DIR / "russian_trusted_root_ca.pem",
        _CERTS_DIR / "russian_trusted_sub_ca.pem",
    ]


@lru_cache(maxsize=1)
def build_ca_bundle_bytes() -> bytes:
    """certifi + Russian Trusted Root/Sub (+ optional SSL_CERT_FILE / TINKOFF_SSL_CA_FILE)."""
    parts: list[bytes] = [Path(certifi.where()).read_bytes()]

    extra = os.getenv("TINKOFF_SSL_CA_FILE") or os.getenv("SSL_CERT_FILE")
    if extra:
        p = Path(extra)
        generated = (_CERTS_DIR / "ca_bundle.pem").resolve()
        if p.is_file() and p.resolve() != generated:
            parts.append(p.read_bytes())

    for pem in _russian_trusted_pem_paths():
        if pem.is_file():
            parts.append(pem.read_bytes())

    return b"\n".join(parts) + b"\n"


def ensure_process_ssl_env() -> Path:
    """
    Write combined CA bundle and point SSL_CERT_FILE / REQUESTS_CA_BUNDLE at it
    so urllib/requests/Sentry also trust Russian Trusted CA.
    """
    bundle = build_ca_bundle_bytes()
    out = _CERTS_DIR / "ca_bundle.pem"
    _CERTS_DIR.mkdir(parents=True, exist_ok=True)
    if not out.is_file() or out.read_bytes() != bundle:
        out.write_bytes(bundle)
    os.environ["SSL_CERT_FILE"] = str(out)
    os.environ["REQUESTS_CA_BUNDLE"] = str(out)
    os.environ["GRPC_DEFAULT_SSL_ROOTS_FILE_PATH"] = str(out)
    return out


def patch_tinkoff_grpc_channel() -> None:
    """Make t_tech.invest Client use CA bundle that includes Russian Trusted CA."""
    import grpc
    from t_tech.invest import channels as invest_channels
    from t_tech.invest.constants import (
        INVEST_GRPC_API,
        KEEPALIVE_MAX_PINGS,
        KEEPALIVE_TIME_MS,
        KEEPALIVE_TIMEOUT_MS,
        MAX_RECEIVE_MESSAGE_LENGTH,
    )

    ensure_process_ssl_env()
    root_certs = build_ca_bundle_bytes()

    if getattr(invest_channels.create_channel, "_capitalview_ssl_patched", False):
        return

    _required_options = [
        ("grpc.max_receive_message_length", MAX_RECEIVE_MESSAGE_LENGTH),
        ("grpc.keepalive_time_ms", KEEPALIVE_TIME_MS),
        ("grpc.keepalive_timeout_ms", KEEPALIVE_TIMEOUT_MS),
        ("grpc.http2.max_pings_without_data", KEEPALIVE_MAX_PINGS),
    ]

    def _with_option(options, key, value):
        for option_name, _ in options:
            if option_name == key:
                return options
        return list(options) + [(key, value)]

    def _with_options(options, required):
        for key, value in required:
            options = _with_option(options, key, value)
        return options

    def create_channel(
        *,
        target=None,
        options=None,
        force_async=False,
        compression=None,
        interceptors=None,
    ):
        creds = grpc.ssl_channel_credentials(root_certificates=root_certs)
        target = target or INVEST_GRPC_API
        if options is None:
            options = []
        options = _with_options(options, _required_options)
        args = (target, creds, options, compression)
        if force_async:
            return grpc.aio.secure_channel(*args, interceptors=interceptors)
        return grpc.secure_channel(*args)

    create_channel._capitalview_ssl_patched = True  # type: ignore[attr-defined]
    invest_channels.create_channel = create_channel
