"""RADIUS client wrappers."""

import os

from pyrad.client import Client
from pyrad.dictionary import Dictionary

# Tentukan path ke dictionary.vendor
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DICT_DIR = os.path.join(BASE_DIR, "freeradius", "dictionary.vendor")

_radius_dict = None


def get_dictionary() -> Dictionary:
    """Memuat FreeRADIUS dictionaries."""
    global _radius_dict
    if _radius_dict is not None:
        return _radius_dict

    # Gunakan dictionary yang sudah didownload
    files = [
        "dictionary.rfc2865",
        "dictionary.rfc2866",
        "dictionary.rfc2869",
        "dictionary.rfc5176",
        "dictionary.mikrotik",
        "dictionary.wispr",
        "dictionary.cambium",
        "dictionary.ubiquiti",
    ]

    dict_paths = [os.path.join(DICT_DIR, f) for f in files if os.path.exists(os.path.join(DICT_DIR, f))]

    if dict_paths:
        _radius_dict = Dictionary(*dict_paths)
    else:
        import pyrad.dictionary

        _radius_dict = pyrad.dictionary.Dictionary("dictionary")

    return _radius_dict


def create_client(nas_ip: str, secret: str, coa_port: int = 3799) -> Client:
    """Membuat RADIUS client untuk CoA/Disconnect."""
    rad_dict = get_dictionary()
    # authport dan acctport disertakan walau tidak dipakai untuk CoA
    client = Client(
        server=nas_ip, secret=secret.encode("utf-8"), dict=rad_dict, authport=1812, acctport=1813, coaport=coa_port
    )
    client.timeout = 3
    client.retries = 2
    return client
