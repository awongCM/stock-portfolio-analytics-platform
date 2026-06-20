#!/bin/bash
# Run the complete ETL pipeline to populate all tables

set -e

echo "=========================================="
echo "Portfolio ETL Pipeline"
echo "=========================================="
echo ""
echo "This will populate:"
echo "  ✓ stock_prices table (historical data)"
echo "  ✓ portfolios table (new portfolio)"
echo "  ✓ transactions table (buy/sell trades)"
echo "  ✓ portfolio_holdings table (auto-calculated)"
echo ""

# Parse arguments
DAYS=30
SYMBOLS="AAPL MSFT GOOGL AMZN TSLA"
PORTFOLIO_NAME="ETL Generated Portfolio"
CASH=100000
SKIP_ICEBERG=""
WATCHLIST=""
REGIONS=""
BASE_CURRENCY="AUD"
NO_FX=""
REQUEST_DELAY="2.0"
BATCH_SIZE="10"

while [[ $# -gt 0 ]]; do
    case $1 in
        --days)
            DAYS="$2"
            shift 2
            ;;
        --symbols)
            SYMBOLS="$2"
            shift 2
            ;;
        --watchlist)
            WATCHLIST="$2"
            shift 2
            ;;
        --regions)
            REGIONS="$2"
            shift 2
            ;;
        --base-currency)
            BASE_CURRENCY="$2"
            shift 2
            ;;
        --no-fx)
            NO_FX="--no-fx"
            shift
            ;;
        --request-delay)
            REQUEST_DELAY="$2"
            shift 2
            ;;
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --portfolio-name)
            PORTFOLIO_NAME="$2"
            shift 2
            ;;
        --cash)
            CASH="$2"
            shift 2
            ;;
        --skip-iceberg)
            SKIP_ICEBERG="--skip-iceberg"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --days N              Number of days of historical data (default: 30)"
            echo "  --symbols \"A B C\"     Space-separated stock symbols (default: AAPL MSFT GOOGL AMZN TSLA)"
            echo "  --watchlist PATH      Sector watchlist YAML (e.g. config/sector_watchlist.yaml)"
            echo "  --regions \"AU SG\"     Filter watchlist regions (AU NZ MY SG)"
            echo "  --base-currency CCY   Base reporting currency (default: AUD)"
            echo "  --no-fx               Skip FX rate ingestion"
            echo "  --request-delay SEC   Delay between Yahoo batch requests (default: 2.0)"
            echo "  --batch-size N        Symbols per batch download (default: 10)"
            echo "  --portfolio-name NAME Name for the portfolio (default: ETL Generated Portfolio)"
            echo "  --cash AMOUNT         Initial cash allocation (default: 100000)"
            echo "  --skip-iceberg        Skip Iceberg export step"
            echo "  --help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --days 60 --cash 50000"
            echo "  $0 --symbols \"AAPL MSFT\" --days 90"
            echo "  $0 --watchlist config/sector_watchlist.yaml --regions \"AU SG\" --days 30"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Configuration:"
echo "  Days of data: $DAYS"
if [[ -n "$WATCHLIST" ]]; then
    echo "  Watchlist: $WATCHLIST"
    echo "  Regions: ${REGIONS:-all}"
    echo "  Base currency: $BASE_CURRENCY"
else
    echo "  Symbols: $SYMBOLS"
fi
echo "  Portfolio: $PORTFOLIO_NAME"
echo "  Initial cash: \$$CASH"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Starting ETL pipeline..."
echo ""

# Run the ETL pipeline (uses mounted /opt/spark-apps volumes)
WATCHLIST_ARG=""
if [[ -n "$WATCHLIST" ]]; then
    WATCHLIST_ARG="--watchlist /opt/spark-apps/$WATCHLIST"
fi

REGION_ARGS=""
if [[ -n "$REGIONS" ]]; then
    REGION_ARGS="--regions $REGIONS"
fi

docker exec portfolio-spark python3 /opt/spark-apps/src/ingestion/etl_pipeline.py \
    --symbols $SYMBOLS \
    --days $DAYS \
    --portfolio-name "$PORTFOLIO_NAME" \
    --initial-cash $CASH \
    --base-currency "$BASE_CURRENCY" \
    --request-delay "$REQUEST_DELAY" \
    --batch-size "$BATCH_SIZE" \
    $WATCHLIST_ARG \
    $REGION_ARGS \
    $NO_FX \
    $SKIP_ICEBERG

echo ""
echo "=========================================="
echo "ETL Pipeline Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. View portfolio: docker exec -it portfolio-postgres psql -U postgres -d portfolio"
echo "  2. Run analytics: ./scripts/test-analytics.sh"
echo "  3. Open Jupyter: http://localhost:8888"
