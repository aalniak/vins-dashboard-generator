#!/bin/bash
#
# VINS-Fusion Dashboard Generator - Build Script
#
# Usage:
#   ./build_dashboard.sh --csv-dir ./data --output ./dashboard
#   ./build_dashboard.sh --csv-dir ./data --rmse ./results.csv --output ./dashboard
#   ./build_dashboard.sh --csv-dir ./data --output ./dashboard --deploy --repo-url https://github.com/user/repo.git

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

CSV_DIR=""
CSV_PATTERN="*.csv"
OUTPUT_DIR="./dashboard"
RMSE_CSV=""
DEPLOY=false
REPO_URL=""
BRANCH="master"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Required:"
    echo "  --csv-dir DIR          Directory containing optimization CSV files"
    echo ""
    echo "Optional:"
    echo "  --pattern PATTERN      Glob pattern for CSV files (default: *.csv)"
    echo "  --output DIR           Output directory (default: ./dashboard)"
    echo "  --rmse FILE            Path to RMSE CSV file"
    echo "  --deploy               Deploy to GitHub Pages"
    echo "  --repo-url URL         Git repository URL (required with --deploy)"
    echo "  --branch BRANCH        Git branch (default: master)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --csv-dir ./data --output ./dashboard"
    echo "  $0 --csv-dir ./data --rmse ./results.csv --output ./dashboard"
    echo "  $0 --csv-dir ./data --output ./dashboard --deploy --repo-url https://github.com/user/repo.git"
}

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

while [[ $# -gt 0 ]]; do
    case $1 in
        --csv-dir) CSV_DIR="$2"; shift 2 ;;
        --pattern) CSV_PATTERN="$2"; shift 2 ;;
        --output) OUTPUT_DIR="$2"; shift 2 ;;
        --rmse) RMSE_CSV="$2"; shift 2 ;;
        --deploy) DEPLOY=true; shift ;;
        --repo-url) REPO_URL="$2"; shift 2 ;;
        --branch) BRANCH="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) log_error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [ -z "$CSV_DIR" ]; then
    log_error "Missing required argument: --csv-dir"
    usage
    exit 1
fi

if [ ! -d "$CSV_DIR" ]; then
    log_error "CSV directory does not exist: $CSV_DIR"
    exit 1
fi

if [ "$DEPLOY" = true ] && [ -z "$REPO_URL" ]; then
    log_error "--deploy requires --repo-url"
    exit 1
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         VINS-Fusion Dashboard Generator                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

log_info "Step 1: Generating static dashboard..."

ARGS=(--csv-dir "$CSV_DIR" --pattern "$CSV_PATTERN" --output "$OUTPUT_DIR")

if [ -n "$RMSE_CSV" ] && [ -f "$RMSE_CSV" ]; then
    ARGS+=(--rmse "$RMSE_CSV")
    log_info "Using RMSE data from: $RMSE_CSV"
fi

python3 "${SCRIPT_DIR}/generate_dashboard.py" "${ARGS[@]}"

log_success "Dashboard generated in: $OUTPUT_DIR"

# Deploy if requested
if [ "$DEPLOY" = true ]; then
    echo ""
    log_info "Step 2: Deploying to GitHub Pages..."
    
    cd "$OUTPUT_DIR"
    
    # Initialize git if needed
    if [ ! -d .git ]; then
        git init
        git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH"
    fi
    
    # Add remote
    if git remote get-url origin &>/dev/null; then
        git remote set-url origin "$REPO_URL"
    else
        git remote add origin "$REPO_URL"
    fi
    
    # Commit and push
    git add -A
    git commit -m "Update dashboard $(date '+%Y-%m-%d %H:%M:%S')" || log_info "No changes to commit"
    git push -u origin "$BRANCH" --force
    
    log_success "Deployed to: $REPO_URL"
    
    # Show GitHub Pages URL
    if [[ "$REPO_URL" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
        OWNER="${BASH_REMATCH[1]}"
        REPO="${BASH_REMATCH[2]}"
        echo ""
        log_success "🌐 GitHub Pages URL: https://${OWNER}.github.io/${REPO}/"
    fi
else
    echo ""
    log_info "To preview: cd $OUTPUT_DIR && python3 -m http.server 8080"
    log_info "To deploy: re-run with --deploy --repo-url <your-repo-url>"
fi

echo ""
