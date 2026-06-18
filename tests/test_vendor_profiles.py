"""Unit tests untuk vendor_profile_service — logika format rate-limit per vendor."""

from app.models.nas_vendor_profiles import NasVendorProfile, RateLimitFormat
from app.services.vendor_profile_service import format_rate_limit, get_all_rate_limit_attributes


def _make_profile(
    vendor_slug: str,
    rate_limit_attribute: str | None,
    rate_limit_format: RateLimitFormat,
    extra_group_reply_attrs: list | None = None,
) -> NasVendorProfile:
    """Helper buat NasVendorProfile tanpa DB."""
    p = NasVendorProfile()
    p.id = 1
    p.vendor_slug = vendor_slug
    p.name = vendor_slug.capitalize()
    p.description = None
    p.rate_limit_attribute = rate_limit_attribute
    p.rate_limit_format = rate_limit_format
    p.extra_group_reply_attrs = extra_group_reply_attrs
    p.is_builtin = True
    p.is_active = True
    return p


class TestMikrotikFormat:
    """Test format Mikrotik-Rate-Limit."""

    def _mikrotik_profile(self) -> NasVendorProfile:
        return _make_profile("mikrotik", "Mikrotik-Rate-Limit", RateLimitFormat.MIKROTIK)

    def test_format_standard_speed(self) -> None:
        """Down/up kbps menghasilkan format 'down k/up k'."""
        profile = self._mikrotik_profile()
        result = format_rate_limit(profile, up_kbps=5120, down_kbps=10240)
        assert result == [("Mikrotik-Rate-Limit", "=", "10240k/5120k")]

    def test_format_unlimited_zero(self) -> None:
        """Speed 0/0 (unlimited) — tidak ada entry radgroupreply."""
        profile = self._mikrotik_profile()
        result = format_rate_limit(profile, up_kbps=0, down_kbps=0)
        # Mikrotik: up=0 dan down=0 → tidak ada rate-limit, list kosong
        # (tidak ada gunanya insert "0/0" ke radgroupreply)
        assert result == []

    def test_format_partial_zero_upload(self) -> None:
        """Upload 0 (unlimited) menghasilkan down k/0."""
        profile = self._mikrotik_profile()
        result = format_rate_limit(profile, up_kbps=0, down_kbps=10240)
        assert result == [("Mikrotik-Rate-Limit", "=", "10240k/0")]

    def test_format_small_speed(self) -> None:
        """Speed kecil (512k/256k)."""
        profile = self._mikrotik_profile()
        result = format_rate_limit(profile, up_kbps=256, down_kbps=512)
        assert result == [("Mikrotik-Rate-Limit", "=", "512k/256k")]


class TestUbiquitiWisprFormat:
    """Test format Ubiquiti WISPr (bps_single_down + extra bps_single_up)."""

    def _ubiquiti_profile(self) -> NasVendorProfile:
        return _make_profile(
            "ubiquiti",
            "WISPr-Bandwidth-Max-Down",
            RateLimitFormat.BPS_SINGLE_DOWN,
            extra_group_reply_attrs=[{"attribute": "WISPr-Bandwidth-Max-Up", "op": "=", "format": "bps_single_up"}],
        )

    def test_format_standard_speed(self) -> None:
        """Down dan up dalam bps (kbps * 1000)."""
        profile = self._ubiquiti_profile()
        result = format_rate_limit(profile, up_kbps=5120, down_kbps=10240)
        assert ("WISPr-Bandwidth-Max-Down", "=", "10240000") in result
        assert ("WISPr-Bandwidth-Max-Up", "=", "5120000") in result
        assert len(result) == 2  # noqa: PLR2004

    def test_format_unlimited(self) -> None:
        """Speed 0 (unlimited) menghasilkan list kosong."""
        profile = self._ubiquiti_profile()
        result = format_rate_limit(profile, up_kbps=0, down_kbps=0)
        assert result == []

    def test_format_down_only(self) -> None:
        """Jika hanya download speed yang diset, hanya down attr yang muncul."""
        profile = self._ubiquiti_profile()
        result = format_rate_limit(profile, up_kbps=0, down_kbps=10240)
        assert ("WISPr-Bandwidth-Max-Down", "=", "10240000") in result
        # Upload 0 — tidak dihasilkan
        assert not any(r[0] == "WISPr-Bandwidth-Max-Up" for r in result)


class TestCiscoIosFormat:
    """Test format Cisco IOS/IOS-XE (cisco_ios)."""

    def _cisco_profile(self) -> NasVendorProfile:
        return _make_profile("cisco", "Cisco-AVPair", RateLimitFormat.CISCO_IOS)

    def test_format_standard_speed(self) -> None:
        """Dua Cisco-AVPair lcp:interface-config rate-limit untuk input dan output."""
        profile = self._cisco_profile()
        result = format_rate_limit(profile, up_kbps=5120, down_kbps=10240)
        assert len(result) == 2  # noqa: PLR2004
        # Input = upload (dari sisi NAS, traffic masuk dari pelanggan)
        assert result[0][0] == "Cisco-AVPair"
        assert result[0][1] == "+="
        assert "rate-limit input 5120000" in result[0][2]
        assert "conform-action transmit exceed-action drop" in result[0][2]
        # Output = download
        assert result[1][0] == "Cisco-AVPair"
        assert "rate-limit output 10240000" in result[1][2]

    def test_format_burst_calculation(self) -> None:
        """Burst = max(8000, bps // 8)."""
        profile = self._cisco_profile()
        result = format_rate_limit(profile, up_kbps=1024, down_kbps=2048)
        # up: 1024 * 1000 = 1024000 bps → burst = max(8000, 1024000 // 8) = 128000
        assert "1024000 128000 128000" in result[0][2]
        # down: 2048 * 1000 = 2048000 bps → burst = max(8000, 2048000 // 8) = 256000
        assert "2048000 256000 256000" in result[1][2]

    def test_format_low_speed_minimum_burst(self) -> None:
        """Speed sangat rendah: burst minimum = 8000 bytes."""
        profile = self._cisco_profile()
        result = format_rate_limit(profile, up_kbps=32, down_kbps=64)
        # up: 32000 bps → burst = max(8000, 32000 // 8) = max(8000, 4000) = 8000
        assert "32000 8000 8000" in result[0][2]

    def test_format_unlimited(self) -> None:
        """Speed 0 (unlimited) menghasilkan list kosong."""
        profile = self._cisco_profile()
        result = format_rate_limit(profile, up_kbps=0, down_kbps=0)
        assert result == []


class TestCambiumFormat:
    """Test format Cambium Networks (kbps_single_down + extra kbps_single_up)."""

    def _cambium_profile(self) -> NasVendorProfile:
        return _make_profile(
            "cambium",
            "Cambium-Canopy-Sustained-Downlink-Rate",
            RateLimitFormat.KBPS_SINGLE_DOWN,
            extra_group_reply_attrs=[
                {
                    "attribute": "Cambium-Canopy-Sustained-Uplink-Rate",
                    "op": "=",
                    "format": "kbps_single_up",
                }
            ],
        )

    def test_format_standard_speed(self) -> None:
        """Down dan up dalam kbps."""
        profile = self._cambium_profile()
        result = format_rate_limit(profile, up_kbps=5120, down_kbps=10240)
        assert ("Cambium-Canopy-Sustained-Downlink-Rate", "=", "10240") in result
        assert ("Cambium-Canopy-Sustained-Uplink-Rate", "=", "5120") in result

    def test_format_unlimited(self) -> None:
        """Speed 0 → list kosong."""
        profile = self._cambium_profile()
        result = format_rate_limit(profile, up_kbps=0, down_kbps=0)
        assert result == []


class TestGenericAndNoneFormat:
    """Test format None / Generic (tidak ada rate-limit)."""

    def test_none_format_returns_empty(self) -> None:
        """Format NONE selalu menghasilkan list kosong."""
        profile = _make_profile("generic", None, RateLimitFormat.NONE)
        result = format_rate_limit(profile, up_kbps=10240, down_kbps=5120)
        assert result == []

    def test_none_attribute_returns_empty(self) -> None:
        """rate_limit_attribute=None selalu menghasilkan list kosong."""
        profile = _make_profile("huawei", None, RateLimitFormat.NONE)
        result = format_rate_limit(profile, up_kbps=10240, down_kbps=5120)
        assert result == []


class TestGetAllRateLimitAttributes:
    """Test helper get_all_rate_limit_attributes()."""

    def test_mikrotik_attributes(self) -> None:
        """Mikrotik hanya punya satu atribut."""
        profile = _make_profile("mikrotik", "Mikrotik-Rate-Limit", RateLimitFormat.MIKROTIK)
        attrs = get_all_rate_limit_attributes(profile)
        assert attrs == ["Mikrotik-Rate-Limit"]

    def test_ubiquiti_attributes(self) -> None:
        """Ubiquiti punya dua atribut (main + extra)."""
        profile = _make_profile(
            "ubiquiti",
            "WISPr-Bandwidth-Max-Down",
            RateLimitFormat.BPS_SINGLE_DOWN,
            extra_group_reply_attrs=[{"attribute": "WISPr-Bandwidth-Max-Up", "op": "=", "format": "bps_single_up"}],
        )
        attrs = get_all_rate_limit_attributes(profile)
        assert "WISPr-Bandwidth-Max-Down" in attrs
        assert "WISPr-Bandwidth-Max-Up" in attrs

    def test_cisco_attributes(self) -> None:
        """Cisco menghasilkan 'Cisco-AVPair' dari format cisco_ios."""
        profile = _make_profile("cisco", "Cisco-AVPair", RateLimitFormat.CISCO_IOS)
        attrs = get_all_rate_limit_attributes(profile)
        # Cisco-AVPair dari rate_limit_attribute + dari cisco_ios format
        assert "Cisco-AVPair" in attrs

    def test_generic_no_attributes(self) -> None:
        """Generic tidak punya atribut."""
        profile = _make_profile("generic", None, RateLimitFormat.NONE)
        attrs = get_all_rate_limit_attributes(profile)
        assert attrs == []
