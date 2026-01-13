# VINS-Fusion Optimization Dashboard Generator

Generate static HTML dashboards from VINS-Fusion optimization CSV files.

## Quick Start

```bash
# Basic usage - just provide CSV directory
python generate_dashboard.py --csv-dir /path/to/csvs --output ./dashboard

# With RMSE data
python generate_dashboard.py --csv-dir /path/to/csvs --rmse /path/to/results.csv --output ./dashboard

# With file pattern
python generate_dashboard.py --csv-dir /path/to/csvs --pattern "P200*.csv" --output ./dashboard
```

Or use the shell script:
```bash
./build_dashboard.sh --csv-dir /path/to/csvs --output ./dashboard
./build_dashboard.sh --csv-dir /path/to/csvs --rmse ./results.csv --output ./dashboard
# With deployment
./build_dashboard.sh \
    --csv-dir /media/SSD \
    --pattern "P200*.csv" \
    --rmse-dir /media/SSD/tartan_out \
    --output ./dashboard \
    --deploy \
    --repo-url https://github.com/aalniak/vinsmono-optimization-results.git
```

## Requirements

```bash
pip install pandas numpy plotly
```

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--csv-dir` | Directory containing CSV files | `.` |
| `--pattern` | Glob pattern for CSV files | `P*.csv` |
| `--output` | Output directory | `./static_dashboard` |
| `--rmse` | Path to RMSE results CSV | None |

## RMSE CSV Format

The RMSE CSV should have:
- `Sequence` column as index (P2001, P2002, etc.)
- Variant columns (baseline, daac_depth_w100, etc.)

Example:
```
Sequence,baseline,daac_depth_w100,gt_depth_opt_w100
P2001,0.8075,0.6491,0.4991
P2002,0.5019,0.4955,0.4594
```

## Output

The generated dashboard includes:
- `index.html` - Main dashboard with all datasets
- `compare.html` - Interactive comparison tool
- `{dataset}.html` - Individual dataset pages with detailed plots
