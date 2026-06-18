"""RADIUS Packet Builder untuk CoA dan Disconnect."""

from pyrad.client import Client
from pyrad.packet import CoAPacket


def build_disconnect_request(client: Client, username: str, session_id: str, framed_ip: str | None = None) -> CoAPacket:
    """Membangun paket Disconnect-Request (Code 40)."""
    req = client.CreateCoAPacket(code=40)

    # Atribut standar RFC 5176
    req.AddAttribute("User-Name", username)
    req.AddAttribute("Acct-Session-Id", str(session_id))

    if framed_ip:
        req.AddAttribute("Framed-IP-Address", framed_ip)

    return req


def build_coa_request(client: Client, username: str, session_id: str) -> CoAPacket:
    """Membangun paket CoA-Request (Code 43)."""
    req = client.CreateCoAPacket(code=43)

    req.AddAttribute("User-Name", username)
    req.AddAttribute("Acct-Session-Id", str(session_id))

    # Atribut lain (rate limit, dsb) akan ditambahkan sesuai profil paket

    return req
