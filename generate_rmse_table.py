#!/usr/bin/env python3
"""
TartanAir Results Table Generator
Scans /media/SSD/tartan_out/* directories and creates comparison tables.
"""

import os
import re
import glob
import pandas as pd
from collections import defaultdict
import argparse

def parse_results_file(filepath):
    """Parse a results.txt file and extract RMSE values.
    
    Returns dict with:
    - all_rmse: list of all RMSE values
    - last_batch_rmse: list of RMSE values from the last experiment batch
    - best_rmse: minimum RMSE
    - last_rmse: last RMSE value
    - mean_rmse: mean of all RMSE values
    """
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Split by "Experiment Batch Start" to get batches
    batches = re.split(r'Experiment Batch Start:', content)
    batches = [b.strip() for b in batches if b.strip()]
    
    all_rmse = []
    last_batch_rmse = []
    
    for i, batch in enumerate(batches):
        # Find all RMSE values in this batch
        rmse_matches = re.findall(r'rmse\s+([\d.]+)', batch, re.IGNORECASE)
        rmse_values = [float(r) for r in rmse_matches]
        all_rmse.extend(rmse_values)
        
        # If this is the last batch, save its values
        if i == len(batches) - 1:
            last_batch_rmse = rmse_values
    
    if not all_rmse:
        return None
    
    return {
        'all_rmse': all_rmse,
        'last_batch_rmse': last_batch_rmse,
        'best_rmse': min(all_rmse),
        'last_rmse': all_rmse[-1] if all_rmse else None,
        'mean_rmse': sum(all_rmse) / len(all_rmse),
        'last_batch_mean': sum(last_batch_rmse) / len(last_batch_rmse) if last_batch_rmse else None,
        'last_batch_best': min(last_batch_rmse) if last_batch_rmse else None,
        'num_runs': len(all_rmse),
    }

def parse_directory_name(dirname):
    """Parse directory name to extract sequence and variant.
    
    Examples:
    - P2001_daac_depth_w100 -> (P2001, daac_depth_w100)
    - P2001base_w0 -> (P2001, base_w0)
    - P2001sdi_w0 -> (P2001, sdi_w0)
    """
    # Pattern: P20XX followed by either _ or directly the variant
    match = re.match(r'(P\d{4})_?(.+)', dirname)
    if match:
        seq = match.group(1)
        variant = match.group(2)
        return seq, variant
    return None, None

def scan_results(base_dir='/media/SSD/tartan_out'):
    """Scan all result directories and collect data."""
    results = defaultdict(dict)  # results[sequence][variant] = data
    
    # Find all directories
    dirs = glob.glob(os.path.join(base_dir, 'P*'))
    
    for dirpath in sorted(dirs):
        dirname = os.path.basename(dirpath)
        results_file = os.path.join(dirpath, 'results.txt')
        
        seq, variant = parse_directory_name(dirname)
        if not seq or not variant:
            print(f"⚠️  Could not parse: {dirname}")
            continue
        
        data = parse_results_file(results_file)
        if data:
            results[seq][variant] = data
        else:
            # Mark as missing/no data
            results[seq][variant] = None
    
    return results

def create_table(results, metric='last_batch_best', outlier_threshold=100.0):
    """Create a pandas DataFrame table from results.
    
    Metrics:
    - best_rmse: Best RMSE across all runs
    - last_rmse: Last RMSE value
    - mean_rmse: Mean of all RMSE values
    - last_batch_mean: Mean of last batch
    - last_batch_best: Best of last batch
    - all_best: Best across ALL runs (ignores batches)
    
    outlier_threshold: Values above this are marked as failures (NaN)
    """
    # Get all sequences and variants
    sequences = sorted(results.keys())
    variants = set()
    for seq_data in results.values():
        variants.update(seq_data.keys())
    variants = sorted(variants)
    
    # Build table data
    table_data = []
    for seq in sequences:
        row = {'Sequence': seq}
        for var in variants:
            data = results[seq].get(var)
            if data and data.get(metric) is not None:
                val = data[metric]
                # Mark outliers as NaN (failed runs)
                if val > outlier_threshold:
                    row[var] = None
                else:
                    row[var] = val
            else:
                row[var] = None
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    df = df.set_index('Sequence')
    
    return df

def highlight_best(df, axis=1):
    """Return a styled DataFrame with best values highlighted."""
    # For RMSE, lower is better
    def highlight_min(s):
        is_min = s == s.min()
        return ['font-weight: bold; color: green' if v else '' for v in is_min]
    
    return df.style.apply(highlight_min, axis=axis)

def print_table(df, title="Results Table"):
    """Print table to console with formatting."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")
    
    # Format floats
    pd.set_option('display.float_format', lambda x: f'{x:.4f}' if pd.notna(x) else '-')
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    
    print(df.to_string())
    
    # Print summary row
    print(f"\n{'─'*80}")
    print("MEAN:  ", end="")
    for col in df.columns:
        mean_val = df[col].mean()
        if pd.notna(mean_val):
            print(f"{col}: {mean_val:.4f}  ", end="")
    print()
    
    # Find best variant (lowest mean RMSE)
    means = df.mean()
    best_variant = means.idxmin()
    print(f"\n🏆 Best variant (lowest mean RMSE): {best_variant} = {means[best_variant]:.4f}")

def export_tables(df, output_dir='/media/SSD'):
    """Export tables to CSV and HTML."""
    csv_path = os.path.join(output_dir, 'results_table.csv')
    html_path = os.path.join(output_dir, 'results_table.html')
    
    # CSV export
    df.to_csv(csv_path)
    print(f"\n📄 CSV saved to: {csv_path}")
    
    # HTML export with styling
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>TartanAir Results Comparison</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        th {{ background: #3498db; color: white; padding: 16px 12px; text-align: center; font-size: 18px; font-weight: bold; }}
        td {{ padding: 14px 12px; text-align: center; border-bottom: 1px solid #ddd; font-size: 20px; }}
        tr:hover {{ background: #f1f8ff; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .best {{ background: #d4edda !important; font-weight: bold; color: #155724; }}
        .worst {{ background: #f8d7da !important; color: #721c24; }}
        .summary {{ background: #fff3cd; font-weight: bold; }}
        .metric-selector {{ margin: 20px 0; text-align: center; }}
        .metric-selector button {{ padding: 10px 20px; margin: 5px; cursor: pointer; border: none; 
                                   background: #3498db; color: white; border-radius: 5px; }}
        .metric-selector button:hover {{ background: #2980b9; }}
        .metric-selector button.active {{ background: #2c3e50; }}
    </style>
</head>
<body>
    <h1>🎯 TartanAir VIO Results Comparison</h1>
    <p style="text-align: center; color: #666;">Generated from /media/SSD/tartan_out/</p>
    
    <h2>📊 RMSE Comparison Table (Lower is Better)</h2>
"""
    
    # Create HTML table with highlighting
    html_content += '<table>\n<tr><th>Sequence</th>'
    for col in df.columns:
        html_content += f'<th>{col}</th>'
    html_content += '</tr>\n'
    
    for idx, row in df.iterrows():
        valid_values = [v for v in row if pd.notna(v)]
        min_val = min(valid_values) if valid_values else None
        max_val = max(valid_values) if valid_values else None
        
        html_content += f'<tr><td><b>{idx}</b></td>'
        for val in row:
            if pd.isna(val):
                html_content += '<td>-</td>'
            else:
                css_class = ''
                if val == min_val:
                    css_class = 'best'
                elif val == max_val and len(valid_values) > 2:
                    css_class = 'worst'
                html_content += f'<td class="{css_class}">{val:.4f}</td>'
        html_content += '</tr>\n'
    
    # Add mean row
    html_content += '<tr class="summary"><td><b>MEAN</b></td>'
    means = df.mean()
    min_mean = means.min()
    for col in df.columns:
        mean_val = means[col]
        css_class = 'best' if mean_val == min_mean else ''
        if pd.notna(mean_val):
            html_content += f'<td class="{css_class}">{mean_val:.4f}</td>'
        else:
            html_content += '<td>-</td>'
    html_content += '</tr>\n'
    
    html_content += '</table>\n'
    
    # Add legend
    html_content += """
    <div style="margin-top: 20px; text-align: center;">
        <span style="background: #d4edda; padding: 5px 10px; margin: 5px;">🟢 Best in row</span>
        <span style="background: #f8d7da; padding: 5px 10px; margin: 5px;">🔴 Worst in row</span>
    </div>
    
    <h2>📈 Summary Statistics</h2>
    <table style="width: auto; margin: 0 auto;">
        <tr><th>Variant</th><th>Mean RMSE</th><th>Std RMSE</th><th>Best Seq</th><th>Worst Seq</th></tr>
"""
    
    for col in df.columns:
        col_data = df[col].dropna()
        if len(col_data) > 0:
            mean_val = col_data.mean()
            std_val = col_data.std()
            best_seq = col_data.idxmin()
            worst_seq = col_data.idxmax()
            css = 'best' if mean_val == min_mean else ''
            html_content += f'<tr class="{css}"><td>{col}</td><td>{mean_val:.4f}</td><td>{std_val:.4f}</td><td>{best_seq}</td><td>{worst_seq}</td></tr>\n'
    
    html_content += """
    </table>
</body>
</html>
"""
    
    with open(html_path, 'w') as f:
        f.write(html_content)
    print(f"🌐 HTML saved to: {html_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate TartanAir results comparison table')
    parser.add_argument('--dir', type=str, default='/media/SSD/tartan_out',
                        help='Base directory containing result folders')
    parser.add_argument('--metric', type=str, default='best_rmse',
                        choices=['best_rmse', 'last_rmse', 'mean_rmse', 'last_batch_mean', 'last_batch_best'],
                        help='Metric to use for comparison (default: best_rmse - best across all runs)')
    parser.add_argument('--outlier', type=float, default=100.0,
                        help='RMSE values above this threshold are marked as failures (default: 100.0)')
    parser.add_argument('--output', type=str, default='/media/SSD',
                        help='Output directory for CSV/HTML files')
    parser.add_argument('--no-export', action='store_true',
                        help='Skip exporting to CSV/HTML')
    parser.add_argument('--exclude', type=str, nargs='*', default=['sdi_w0'],
                        help='Variants to exclude (default: sdi_w0)')
    parser.add_argument('--variants', type=str, nargs='*', default=None,
                        help='Only include these variants (e.g., --variants baseline daac_depth_w100). Overrides --exclude.')
    parser.add_argument('--rename', type=str, nargs='*', default=['base_w0=baseline'],
                        help='Rename variants (format: old=new, default: base_w0=baseline)')
    
    args = parser.parse_args()
    
    print(f"🔍 Scanning results in: {args.dir}")
    results = scan_results(args.dir)
    
    print(f"📊 Found {len(results)} sequences")
    
    # Create table
    df = create_table(results, metric=args.metric, outlier_threshold=args.outlier)
    
    # Rename variants first (so --variants can use new names)
    if args.rename:
        rename_map = {}
        for r in args.rename:
            if '=' in r:
                old, new = r.split('=', 1)
                if old in df.columns:
                    rename_map[old] = new
        if rename_map:
            df = df.rename(columns=rename_map)
            print(f"📝 Renamed: {rename_map}")
    
    # Filter to specific variants if --variants is provided
    if args.variants:
        keep_cols = [v for v in args.variants if v in df.columns]
        missing = [v for v in args.variants if v not in df.columns]
        if missing:
            print(f"⚠️  Variants not found: {missing}")
        if keep_cols:
            df = df[keep_cols]
            print(f"✅ Selected variants: {keep_cols}")
    else:
        # Otherwise use exclude
        if args.exclude:
            for excl in args.exclude:
                if excl in df.columns:
                    df = df.drop(columns=[excl])
                    print(f"🚫 Excluded variant: {excl}")
    
    # Print to console
    print_table(df, title=f"RMSE Comparison ({args.metric})")
    
    # Export
    if not args.no_export:
        export_tables(df, args.output)
    
    print("\n✅ Done!")

if __name__ == '__main__':
    main()
