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
            echo "  --portfolio-name NAME Name for the portfolio (default: ETL Generated Portfolio)"
            echo "  --cash AMOUNT         Initial cash allocation (default: 100000)"
            echo "  --skip-iceberg        Skip Iceberg export step"
            echo "  --help                Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --days 60 --cash 50000"
            echo "  $0 --symbols \"AAPL MSFT\" --days 90"
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
echo "  Symbols: $SYMBOLS"
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

# Copy the ETL script to container
docker cp src/ingestion/etl_pipeline.py portfolio-spark:/tmp/etl_pipeline.py

# Run the ETL pipeline
docker exec portfolio-spark python3 /tmp/etl_pipeline.py \
    --symbols $SYMBOLS \
    --days $DAYS \
    --portfolio-name "$PORTFOLIO_NAME" \
    --initial-cash $CASH \
    $SKIP_ICEBERG

# Clean up
docker exec portfolio-spark rm /tmp/etl_pipeline.py

echo ""
echo "=========================================="
echo "ETL Pipeline Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. View portfolio: docker exec -it portfolio-postgres psql -U postgres -d portfolio"
echo "  2. Run analytics: ./scripts/test-analytics.sh"
echo "  3. Open Jupyter: http://localhost:8888"
