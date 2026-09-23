"""Canonicalize exact network destinations without resolving DNS."""

from __future__ import annotations

import ipaddress
import re
import unicodedata
from urllib.parse import urlsplit


METADATA_HOSTS = {
    "metadata.google.internal",
    "metadata.goog",
    "instance-data.ec2.internal",
}
METADATA_IPS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
    ipaddress.ip_address("fd00:ec2::254"),
}
HOST_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
NUMERIC_HOST_RE = re.compile(r"(?i)^(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*$")


def _has_control(value: str) -> bool:
    return any(unicodedata.category(character).startswith("C") for character in value)


def _metadata_ip(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if address in METADATA_IPS or address.is_link_local:
        return True
    mapped = getattr(address, "ipv4_mapped", None)
    return bool(mapped and (mapped in METADATA_IPS or mapped.is_link_local))


def _canonical_host(value: str) -> tuple[str | None, str | None]:
    host = value.rstrip(".").casefold()
    if not host or "%" in host or _has_control(host):
        return None, "invalid"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if NUMERIC_HOST_RE.fullmatch(host):
            return None, "invalid"
        try:
            host = host.encode("idna").decode("ascii").casefold()
        except UnicodeError:
            return None, "invalid"
        labels = host.split(".")
        if len(host) > 253 or any(not HOST_LABEL_RE.fullmatch(label) for label in labels):
            return None, "invalid"
        if host in METADATA_HOSTS:
            return None, "metadata"
        return host, None
    if _metadata_ip(address):
        return None, "metadata"
    return f"[{address.compressed}]" if address.version == 6 else address.compressed, None


def _canonical_port(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        port = int(value)
    except (TypeError, ValueError):
        return None
    return port if 0 < port <= 65_535 else None


def _canonical_url(value: str) -> tuple[str | None, str | None]:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None, "invalid"
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or parsed.username is not None or parsed.password is not None:
        return None, "invalid"
    if not parsed.hostname:
        return None, "invalid"
    host, error = _canonical_host(parsed.hostname)
    if error or host is None:
        return None, error
    canonical_port = _canonical_port(port if port is not None else (443 if scheme == "https" else 80))
    if canonical_port is None:
        return None, "invalid"
    return f"{host}:{canonical_port}", None


def _canonical_cidr(value: str) -> tuple[str | None, str | None]:
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError:
        return None, "invalid"
    if network.prefixlen == 0 or network.is_link_local:
        return None, "metadata" if network.is_link_local else "invalid"
    for address in METADATA_IPS:
        if address.version == network.version and address in network:
            return None, "metadata"
    return f"cidr:{network.with_prefixlen}", None


def canonical_network_destination(value: object) -> tuple[str | None, str | None]:
    """Return a comparison-safe destination and a static error category."""
    if not isinstance(value, str) or not value or len(value) > 2_048:
        return None, "invalid"
    if value != value.strip() or _has_control(value) or "*" in value:
        return None, "invalid"
    if "://" in value:
        return _canonical_url(value)
    if "/" in value:
        return _canonical_cidr(value)

    if value.startswith("["):
        try:
            parsed = urlsplit(f"//{value}")
            port = parsed.port
        except ValueError:
            return None, "invalid"
        if not parsed.hostname or parsed.path or parsed.username is not None or parsed.password is not None:
            return None, "invalid"
        host_value = parsed.hostname
    elif value.count(":") == 1:
        host_value, raw_port = value.rsplit(":", 1)
        port = _canonical_port(raw_port)
    else:
        return None, "invalid"

    canonical_port = _canonical_port(port)
    if canonical_port is None:
        return None, "invalid"
    host, error = _canonical_host(host_value)
    if error or host is None:
        return None, error
    return f"{host}:{canonical_port}", None
