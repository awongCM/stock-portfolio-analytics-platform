"""Unit tests for sector watchlist loading."""

import pytest
from pathlib import Path

EXPECTED_GICS_SECTORS = {
    "Energy", "Materials", "Industrials", "Utilities", "Healthcare",
    "Financials", "Consumer Discretionary", "Consumer Staples",
    "Information Technology", "Communication Services", "Real Estate",
}


class TestWatchlistLoading:
    """Tests for multi-region watchlist YAML parsing."""

    @pytest.fixture
    def watchlist_path(self):
        return str(
            Path(__file__).resolve().parents[1] / "config" / "sector_watchlist.yaml"
        )

    def test_load_watchlist_all_regions(self, watchlist_path):
        import yaml
        with open(watchlist_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert config["base_currency"] == "AUD"
        assert len(config["regions"]) == 4
        assert len(config["sectors"]) == 11
        assert len(config["fx_pairs"]) >= 4

        symbols = []
        for sector, regions in config["sectors"].items():
            assert sector in EXPECTED_GICS_SECTORS
            for region, tickers in regions.items():
                assert region in config["regions"]
                for t in tickers:
                    symbols.append(t.upper())

        # 11 sectors × 4 regions × ~2-3 tickers = 88-132
        assert 80 <= len(symbols) <= 140
        assert all(s == s.upper() for s in symbols)

    def test_load_watchlist_region_filter(self, watchlist_path):
        import yaml
        with open(watchlist_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        au_symbols = []
        for sector, regions in config["sectors"].items():
            for t in regions.get("AU", []):
                au_symbols.append(t.upper())

        assert len(au_symbols) >= 22  # 11 sectors × 2 min
        assert all(s.endswith(".AX") for s in au_symbols)
