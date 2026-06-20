"""Stock data ingestion from external APIs to Supabase."""

import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import yaml
import yfinance as yf
import pandas as pd
from sqlalchemy import text
from ..utils.supabase_client import get_postgres_engine

# Yahoo suffix → market metadata (fallback when watchlist not used)
SUFFIX_MARKET_MAP = {
    ".AX": ("ASX", "AU", "AUD"),
    ".NZ": ("NZX", "NZ", "NZD"),
    ".KL": ("BURSA", "MY", "MYR"),
    ".SI": ("SGX", "SG", "SGD"),
}

GICS_CODE_MAP = {
    "Energy": "energy",
    "Materials": "materials",
    "Industrials": "industrials",
    "Utilities": "utilities",
    "Healthcare": "healthcare",
    "Financials": "financials",
    "Consumer Discretionary": "consumer_discretionary",
    "Consumer Staples": "consumer_staples",
    "Information Technology": "information_technology",
    "Communication Services": "communication_services",
    "Real Estate": "real_estate",
}


class StockDataIngestion:
    """Handles stock data ingestion from Yahoo Finance."""

    def __init__(self):
        self.engine = get_postgres_engine()
        self._gics_sector_ids: Optional[Dict[str, int]] = None
        self._market_ids: Optional[Dict[str, int]] = None

    def _load_reference_ids(self) -> None:
        """Cache gics_sectors and markets lookup tables."""
        if self._gics_sector_ids is not None:
            return
        self._gics_sector_ids = {}
        self._market_ids = {}
        with self.engine.connect() as conn:
            for row in conn.execute(text("SELECT id, code FROM gics_sectors")):
                self._gics_sector_ids[row[1]] = row[0]
            for row in conn.execute(text("SELECT id, code FROM markets")):
                self._market_ids[row[1]] = row[0]

    def load_watchlist(
        self,
        watchlist_path: str,
        regions: Optional[List[str]] = None,
    ) -> Tuple[List[str], Dict[str, Dict[str, Any]], List[str], str]:
        """
        Load symbols and metadata from sector watchlist YAML.

        Returns:
            (symbols, symbol_metadata, fx_pairs, base_currency)
        """
        path = Path(watchlist_path)
        if not path.is_absolute():
            repo_root = Path(__file__).resolve().parents[2]
            path = repo_root / watchlist_path

        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        base_currency = config.get("base_currency", "AUD")
        fx_pairs = config.get("fx_pairs", [])
        region_filter = {r.upper() for r in regions} if regions else None

        symbols: List[str] = []
        symbol_metadata: Dict[str, Dict[str, Any]] = {}
        regions_config = config.get("regions", {})
        sectors = config.get("sectors", {})

        for sector_name, region_symbols in sectors.items():
            gics_code = GICS_CODE_MAP.get(sector_name, sector_name.lower().replace(" ", "_"))
            for region_code, tickers in region_symbols.items():
                if region_filter and region_code.upper() not in region_filter:
                    continue
                region_meta = regions_config.get(region_code, {})
                for ticker in tickers:
                    symbol = ticker.upper()
                    if symbol not in symbol_metadata:
                        symbols.append(symbol)
                        symbol_metadata[symbol] = {
                            "gics_sector_code": gics_code,
                            "gics_sector_override": sector_name,
                            "country_code": region_meta.get("country_code"),
                            "quote_currency": region_meta.get("quote_currency"),
                            "market_code": region_meta.get("market_code"),
                        }

        return symbols, symbol_metadata, fx_pairs, base_currency

    def _infer_market_from_symbol(self, symbol: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Infer market/country/currency from Yahoo suffix."""
        for suffix, (market_code, country, currency) in SUFFIX_MARKET_MAP.items():
            if symbol.upper().endswith(suffix.upper()):
                return market_code, country, currency
        return None, None, "USD"

    def ensure_stock_exists(
        self,
        symbol: str,
        metadata: Optional[Dict[str, Any]] = None,
        skip_yfinance_info: bool = False,
    ) -> str:
        """Ensure stock record exists, enriching with region/GICS metadata."""
        symbol = symbol.upper()
        metadata = metadata or {}

        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT id FROM stocks WHERE symbol = :symbol"),
                {"symbol": symbol},
            ).fetchone()
            if result:
                stock_id = result[0]
                if metadata:
                    self._update_stock_metadata(conn, stock_id, symbol, metadata)
                    conn.commit()
                return stock_id

        market_code = metadata.get("market_code")
        country_code = metadata.get("country_code")
        quote_currency = metadata.get("quote_currency")
        gics_override = metadata.get("gics_sector_override")
        if not market_code:
            market_code, country_code, quote_currency = self._infer_market_from_symbol(symbol)

        name = symbol
        exchange = market_code or ""
        sector = gics_override or ""
        industry = ""

        if not skip_yfinance_info and not gics_override:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            name = info.get("longName") or info.get("shortName") or symbol
            exchange = info.get("exchange") or exchange
            sector = info.get("sector") or sector
            industry = info.get("industry") or industry
            country_code = country_code or info.get("country")
            quote_currency = quote_currency or info.get("currency") or "USD"

        gics_sector_id = None
        if metadata.get("gics_sector_code"):
            self._load_reference_ids()
            gics_sector_id = self._gics_sector_ids.get(metadata["gics_sector_code"])

        market_id = None
        if market_code:
            self._load_reference_ids()
            market_id = self._market_ids.get(market_code)

        stock_data = {
            "symbol": symbol,
            "name": name,
            "exchange": exchange,
            "sector": gics_override or sector,
            "industry": industry,
            "country_code": country_code,
            "quote_currency": quote_currency or "USD",
            "gics_sector_id": gics_sector_id,
            "market_id": market_id,
            "gics_sector_override": gics_override,
        }

        with self.engine.connect() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO stocks (
                        symbol, name, exchange, sector, industry,
                        country_code, quote_currency, gics_sector_id,
                        market_id, gics_sector_override
                    )
                    VALUES (
                        :symbol, :name, :exchange, :sector, :industry,
                        :country_code, :quote_currency, :gics_sector_id,
                        :market_id, :gics_sector_override
                    )
                    RETURNING id
                """),
                stock_data,
            )
            conn.commit()
            return result.fetchone()[0]

    def _update_stock_metadata(
        self,
        conn,
        stock_id: str,
        symbol: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Update existing stock with watchlist metadata."""
        self._load_reference_ids()
        gics_sector_id = self._gics_sector_ids.get(metadata.get("gics_sector_code", ""))
        market_id = self._market_ids.get(metadata.get("market_code", ""))

        conn.execute(
            text("""
                UPDATE stocks SET
                    country_code = COALESCE(:country_code, country_code),
                    quote_currency = COALESCE(:quote_currency, quote_currency),
                    gics_sector_id = COALESCE(:gics_sector_id, gics_sector_id),
                    market_id = COALESCE(:market_id, market_id),
                    gics_sector_override = COALESCE(:gics_sector_override, gics_sector_override),
                    sector = COALESCE(:gics_sector_override, sector),
                    updated_at = NOW()
                WHERE id = :stock_id
            """),
            {
                "stock_id": stock_id,
                "country_code": metadata.get("country_code"),
                "quote_currency": metadata.get("quote_currency"),
                "gics_sector_id": gics_sector_id,
                "market_id": market_id,
                "gics_sector_override": metadata.get("gics_sector_override"),
            },
        )

    def fetch_stock_prices(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo",
    ) -> pd.DataFrame:
        """Fetch stock prices from Yahoo Finance."""
        ticker = yf.Ticker(symbol)
        if start_date and end_date:
            df = ticker.history(start=start_date, end=end_date)
        else:
            df = ticker.history(period=period)
        return df

    def ingest_stock_prices(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Ingest stock prices into Supabase."""
        symbol = symbol.upper()
        stock_id = self.ensure_stock_exists(symbol, metadata)
        df = self.fetch_stock_prices(symbol, start_date, end_date, period)

        if df.empty:
            print(f"No data fetched for {symbol}")
            return 0

        records = []
        for timestamp, row in df.iterrows():
            records.append({
                "stock_id": stock_id,
                "timestamp": timestamp.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
                "adjusted_close": float(row["Close"]),
            })

        batch_size = 1000
        inserted_count = 0
        with self.engine.connect() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                try:
                    for record in batch:
                        conn.execute(
                            text("""
                                INSERT INTO stock_prices
                                (stock_id, timestamp, open, high, low, close, volume, adjusted_close)
                                VALUES (:stock_id, :timestamp, :open, :high, :low, :close, :volume, :adjusted_close)
                                ON CONFLICT (stock_id, timestamp) DO UPDATE SET
                                    open = EXCLUDED.open,
                                    high = EXCLUDED.high,
                                    low = EXCLUDED.low,
                                    close = EXCLUDED.close,
                                    volume = EXCLUDED.volume,
                                    adjusted_close = EXCLUDED.adjusted_close
                            """),
                            record,
                        )
                    conn.commit()
                    inserted_count += len(batch)
                except Exception as e:
                    print(f"Error inserting batch for {symbol}: {e}")
                    conn.rollback()

        print(f"Ingested {inserted_count} price records for {symbol}")
        return inserted_count

    def _symbol_price_frame(self, symbol: str, data: pd.DataFrame) -> pd.DataFrame:
        """Extract OHLCV rows for one symbol from a yfinance download result."""
        if data.empty:
            return pd.DataFrame()

        if isinstance(data.columns, pd.MultiIndex):
            if symbol not in data.columns.get_level_values(0):
                return pd.DataFrame()
            return data[symbol].dropna(how="all")

        if len(data.columns) == 1:
            return pd.DataFrame()
        return data

    def _insert_price_records(self, stock_id: str, symbol: str, df: pd.DataFrame) -> int:
        """Persist OHLCV rows for a stock."""
        if df.empty:
            return 0

        records = []
        for timestamp, row in df.iterrows():
            if pd.isna(row.get("Close")):
                continue
            records.append({
                "stock_id": stock_id,
                "timestamp": timestamp.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]) if not pd.isna(row.get("Volume")) else 0,
                "adjusted_close": float(row["Close"]),
            })

        batch_size = 1000
        inserted_count = 0
        with self.engine.connect() as conn:
            for i in range(0, len(records), batch_size):
                batch = records[i : i + batch_size]
                try:
                    for record in batch:
                        conn.execute(
                            text("""
                                INSERT INTO stock_prices
                                (stock_id, timestamp, open, high, low, close, volume, adjusted_close)
                                VALUES (:stock_id, :timestamp, :open, :high, :low, :close, :volume, :adjusted_close)
                                ON CONFLICT (stock_id, timestamp) DO UPDATE SET
                                    open = EXCLUDED.open,
                                    high = EXCLUDED.high,
                                    low = EXCLUDED.low,
                                    close = EXCLUDED.close,
                                    volume = EXCLUDED.volume,
                                    adjusted_close = EXCLUDED.adjusted_close
                            """),
                            record,
                        )
                    conn.commit()
                    inserted_count += len(batch)
                except Exception as e:
                    print(f"Error inserting batch for {symbol}: {e}")
                    conn.rollback()

        return inserted_count

    def _download_prices(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo",
        request_delay: float = 2.0,
        batch_size: int = 10,
    ) -> Dict[str, pd.DataFrame]:
        """Download prices in batches to reduce Yahoo Finance rate limiting."""
        frames: Dict[str, pd.DataFrame] = {}

        for i in range(0, len(symbols), batch_size):
            batch = [s.upper() for s in symbols[i : i + batch_size]]
            if i > 0 and request_delay > 0:
                time.sleep(request_delay)

            for attempt in range(3):
                try:
                    if start_date and end_date:
                        data = yf.download(
                            tickers=" ".join(batch),
                            start=start_date,
                            end=end_date,
                            group_by="ticker",
                            auto_adjust=True,
                            threads=False,
                            progress=False,
                        )
                    else:
                        data = yf.download(
                            tickers=" ".join(batch),
                            period=period,
                            group_by="ticker",
                            auto_adjust=True,
                            threads=False,
                            progress=False,
                        )

                    if len(batch) == 1:
                        frames[batch[0]] = self._symbol_price_frame(batch[0], data)
                    else:
                        for symbol in batch:
                            frames[symbol] = self._symbol_price_frame(symbol, data)
                    break
                except Exception as e:
                    if attempt < 2 and "Rate" in str(e):
                        wait = request_delay * (2 ** (attempt + 1))
                        print(f"Rate limited on batch {batch[:3]}..., retrying in {wait:.0f}s")
                        time.sleep(wait)
                    else:
                        for symbol in batch:
                            frames.setdefault(symbol, pd.DataFrame())
                        print(f"Batch download failed for {batch}: {e}")

        return frames

    def ingest_fx_rates(
        self,
        fx_pairs: List[str],
        base_currency: str = "AUD",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo",
    ) -> int:
        """Ingest daily FX rates from Yahoo Finance currency pairs."""
        total = 0
        for pair in fx_pairs:
            pair = pair.upper()
            try:
                df = self.fetch_stock_prices(pair, start_date, end_date, period)
                if df.empty:
                    print(f"No FX data for {pair}")
                    continue

                clean = pair.replace("=X", "")
                if len(clean) >= 6:
                    pair_base, pair_quote = clean[:3], clean[3:6]
                else:
                    continue

                records = []
                for timestamp, row in df.iterrows():
                    records.append({
                        "base_currency": pair_base,
                        "quote_currency": pair_quote,
                        "timestamp": timestamp.isoformat(),
                        "rate": float(row["Close"]),
                    })

                with self.engine.connect() as conn:
                    for record in records:
                        conn.execute(
                            text("""
                                INSERT INTO exchange_rates
                                (base_currency, quote_currency, timestamp, rate)
                                VALUES (:base_currency, :quote_currency, :timestamp, :rate)
                                ON CONFLICT (base_currency, quote_currency, timestamp) DO UPDATE SET
                                    rate = EXCLUDED.rate
                            """),
                            record,
                        )
                    conn.commit()
                    total += len(records)
                    print(f"Ingested {len(records)} FX records for {pair}")
            except Exception as e:
                print(f"Error ingesting FX {pair}: {e}")

        return total

    def ingest_watchlist(
        self,
        watchlist_path: str,
        regions: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ingest_fx: bool = True,
        request_delay: float = 2.0,
        batch_size: int = 10,
    ) -> Dict[str, int]:
        """Ingest all symbols from sector watchlist plus FX rates."""
        symbols, metadata_map, fx_pairs, base_currency = self.load_watchlist(
            watchlist_path, regions
        )
        results: Dict[str, int] = {}

        stock_ids: Dict[str, str] = {}
        for symbol in symbols:
            try:
                stock_ids[symbol] = self.ensure_stock_exists(
                    symbol,
                    metadata_map.get(symbol),
                    skip_yfinance_info=True,
                )
            except Exception as e:
                print(f"Error registering {symbol}: {e}")

        price_frames = self._download_prices(
            [s for s in symbols if s in stock_ids],
            start_date=start_date,
            end_date=end_date,
            request_delay=request_delay,
            batch_size=batch_size,
        )

        for symbol, df in price_frames.items():
            try:
                if df.empty:
                    print(f"No data fetched for {symbol}")
                    results[symbol] = 0
                    continue
                count = self._insert_price_records(stock_ids[symbol], symbol, df)
                results[symbol] = count
                print(f"Ingested {count} price records for {symbol}")
            except Exception as e:
                print(f"Error ingesting {symbol}: {e}")
                results[symbol] = 0

        if ingest_fx and fx_pairs:
            if request_delay > 0:
                time.sleep(request_delay)
            fx_count = self.ingest_fx_rates(
                fx_pairs,
                base_currency=base_currency,
                start_date=start_date,
                end_date=end_date,
            )
            results["__fx__"] = fx_count

        return results

    def ingest_multiple_stocks(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "1mo",
        symbol_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, int]:
        """Ingest price data for multiple stocks."""
        results = {}
        symbol_metadata = symbol_metadata or {}
        for symbol in symbols:
            try:
                count = self.ingest_stock_prices(
                    symbol,
                    start_date,
                    end_date,
                    period,
                    metadata=symbol_metadata.get(symbol.upper()),
                )
                results[symbol] = count
            except Exception as e:
                print(f"Error ingesting {symbol}: {e}")
                results[symbol] = 0
        return results
