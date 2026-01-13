#!/usr/bin/env python3
"""
Static Dashboard Exporter for GitHub Pages
Converts the Dash visualization to static HTML files with interactive Plotly charts.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import argparse
import os
import glob
from datetime import datetime

# Global RMSE data
RMSE_DATA = None

def load_rmse_data(rmse_csv_path=None):
    """Load RMSE data from CSV file."""
    global RMSE_DATA
    if rmse_csv_path and os.path.exists(rmse_csv_path):
        RMSE_DATA = pd.read_csv(rmse_csv_path, index_col='Sequence')
        print(f"📊 Loaded RMSE data from: {rmse_csv_path}")
    return RMSE_DATA

def get_rmse(name):
    """Get RMSE value for a dataset based on naming pattern.
    
    Handles naming convention mismatches between CSV files and RMSE table:
    - CSV: P2001_base.csv, P2001_daac_depth_opt_w100.csv, P2001_gt_depth_rgd_inverse.csv
    - RMSE table: baseline, daac_depth_w100, gt_depth_rgd_inv_w0
    """
    if RMSE_DATA is None:
        return None
    
    import re
    match = re.match(r'(P\d{4})_?(.*)', name)
    if not match:
        return None
    
    seq = match.group(1)
    variant = match.group(2) if match.group(2) else 'base'
    
    # Special case: P2001_outlier_opt has a fixed RMSE value
    if name == 'P2001_outlier_opt':
        return 0.4386
    
    # Special case: gt_depth_sdi uses the same RMSE as base
    if variant == 'gt_depth_sdi':
        variant = 'base'
    
    # Map CSV variant names to possible RMSE column names (try multiple)
    # Format: csv_variant -> [possible_rmse_columns]
    variant_to_columns = {
        'base': ['baseline', 'base_w0', 'base'],
        'daac_depth_opt_w100': ['daac_depth_w100', 'daac_depth_opt_w100'],
        'daac_rgd_inv': ['daac_rgd_inv_w0', 'daac_rgd_inv'],
        'daac_rgd_metric': ['daac_rgd_metric_w0', 'daac_rgd_metric'],
        'gt_depth_opt_w100': ['gt_depth_opt_w100'],
        'gt_depth_rgd_inverse': ['gt_depth_rgd_inv_w0', 'gt_depth_rgd_inverse', 'gt_depth_rgd_inv'],
        'gt_depth_rgd_metric': ['gt_depth_rgd_metric_w0', 'gt_depth_rgd_metric'],
    }
    
    # Get possible column names for this variant
    possible_columns = variant_to_columns.get(variant, [variant])
    
    # Check sequence exists
    if seq not in RMSE_DATA.index:
        return None
    
    # Try each possible column name
    for column in possible_columns:
        if column in RMSE_DATA.columns:
            value = RMSE_DATA.loc[seq, column]
            if not pd.isna(value):
                return value
    
    return None

def get_description(name):
    """Get description for a dataset based on naming pattern."""
    # Extract sequence (P200X) and variant
    import re
    match = re.match(r'(P\d{4})_?(.*)', name)
    if not match:
        return name
    
    seq = match.group(1)
    variant = match.group(2) if match.group(2) else 'base'
    
    descriptions = {
        'base': f'{seq} Baseline Diagnostics',
        'daac_depth_opt_w100': f'{seq} DAAC Depth into Optimization with Weight=100',
        'daac_rgd_inv': f'{seq} DAAC RGD with Log-scale Inverse Depth Visualization (15% Depth + 85% Image)',
        'daac_rgd_metric': f'{seq} DAAC RGD with Log-scale Metric Depth Visualization (15% Depth + 85% Image)',
        'gt_depth_opt_w100': f'{seq} GT Depth into Optimization with Weight=100',
        'gt_depth_opt': f'{seq} GT Depth into Optimization with Weight=100',  # Legacy name
        'gt_depth_rgd_inverse': f'{seq} GT Depth RGD with Log-scale Inverse Depth Visualization (15% Depth + 85% Image)',
        'gt_depth_rgd_metric': f'{seq} GT Depth RGD with Log-scale Metric Depth Visualization (15% Depth + 85% Image)',
        'gt_depth_sdi': f'{seq} GT Depth Smart Depth Initialization (spoiler: had no effect)',
        'depth_opt': f'{seq} Depth Optimization',
        'outlier_opt': f'{seq} Outlier Optimization',
    }
    
    return descriptions.get(variant, f'{seq} {variant}')

def get_short_variant(name):
    """Get short variant name for display."""
    import re
    match = re.match(r'P\d{4}_?(.*)', name)
    if match and match.group(1):
        return match.group(1)
    return 'baseline'

def load_and_clean_data(csv_path):
    """Load CSV and remove the last (potentially corrupted) row."""
    df = pd.read_csv(csv_path)
    df = df.iloc[:-1].copy()
    df = df.reset_index(drop=True)
    return df

def create_total_cost_figure(df, title_suffix=""):
    """Total cost before/after optimization."""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Total Cost: Initial vs Final', 'Cost Reduction Over Time'),
        vertical_spacing=0.12,
        row_heights=[0.6, 0.4]
    )
    
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['total_cost_init'], mode='lines+markers',
                             name='Initial Cost', line=dict(color='#EF553B', width=2), marker=dict(size=4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['total_cost_final'], mode='lines+markers',
                             name='Final Cost', line=dict(color='#00CC96', width=2), marker=dict(size=4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['total_reduction_pct'], mode='lines',
                             name='Reduction %', fill='tozeroy', line=dict(color='#636EFA', width=2)), row=2, col=1)
    
    avg_reduction = df['total_reduction_pct'].mean()
    fig.add_hline(y=avg_reduction, line_dash="dash", line_color="orange", 
                  annotation_text=f"Avg: {avg_reduction:.1f}%", row=2, col=1)
    
    fig.update_yaxes(type="log", title_text="Cost (log scale)", row=1, col=1)
    fig.update_yaxes(title_text="Reduction %", row=2, col=1)
    fig.update_xaxes(title_text="Frame ID", row=2, col=1)
    fig.update_layout(height=600, title_text=f"<b>Overall Optimization Performance{title_suffix}</b>", title_x=0.5,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), hovermode='x unified')
    return fig

def create_visual_cost_figure(df, title_suffix=""):
    """Visual reprojection cost."""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Visual Reprojection Cost: Initial vs Final', 'Visual Cost Reduction & Factor Count'),
        vertical_spacing=0.12, row_heights=[0.6, 0.4],
        specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
    )
    
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['visual_cost_init'], mode='lines+markers',
                             name='Visual Initial', line=dict(color='#EF553B', width=2), marker=dict(size=4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['visual_cost_final'], mode='lines+markers',
                             name='Visual Final', line=dict(color='#00CC96', width=2), marker=dict(size=4)), row=1, col=1)
    
    df['total_visual_factors'] = df['num_visual_mono_factors'] + df['num_visual_stereo_factors'] + df['num_visual_one_frame_factors']
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['visual_reduction_pct'], mode='lines',
                             name='Reduction %', fill='tozeroy', line=dict(color='#636EFA', width=2)), row=2, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['total_visual_factors'], mode='lines',
                             name='# Factors', line=dict(color='#FFA15A', width=2, dash='dot')), row=2, col=1, secondary_y=True)
    
    fig.update_yaxes(type="log", title_text="Cost (log scale)", row=1, col=1)
    fig.update_yaxes(title_text="Reduction %", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="# Factors", row=2, col=1, secondary_y=True)
    fig.update_layout(height=600, title_text=f"<b>Visual Reprojection Factor Analysis{title_suffix}</b>", title_x=0.5,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), hovermode='x unified')
    return fig

def create_imu_cost_figure(df, title_suffix=""):
    """IMU preintegration cost."""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('IMU Factor Cost: Initial vs Final', 'IMU Cost Reduction & Factor Count'),
        vertical_spacing=0.12, row_heights=[0.6, 0.4],
        specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
    )
    
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['imu_cost_init'], mode='lines+markers',
                             name='IMU Initial', line=dict(color='#EF553B', width=2), marker=dict(size=4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['imu_cost_final'], mode='lines+markers',
                             name='IMU Final', line=dict(color='#00CC96', width=2), marker=dict(size=4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['imu_reduction_pct'], mode='lines',
                             name='Reduction %', fill='tozeroy', line=dict(color='#636EFA', width=2)), row=2, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['num_imu_factors'], mode='lines',
                             name='# Factors', line=dict(color='#FFA15A', width=2, dash='dot')), row=2, col=1, secondary_y=True)
    
    fig.update_yaxes(type="log", title_text="Cost (log scale)", row=1, col=1)
    fig.update_yaxes(title_text="Reduction %", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="# Factors", row=2, col=1, secondary_y=True)
    fig.update_layout(height=600, title_text=f"<b>IMU Preintegration Factor Analysis{title_suffix}</b>", title_x=0.5,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), hovermode='x unified')
    return fig

def create_depth_cost_figure(df, title_suffix=""):
    """Depth prior cost."""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Depth Prior Cost: Initial vs Final', 'Depth Cost Reduction & Factor Count'),
        vertical_spacing=0.12, row_heights=[0.6, 0.4],
        specs=[[{"secondary_y": False}], [{"secondary_y": True}]]
    )
    
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['depth_cost_init'], mode='lines+markers',
                             name='Depth Initial', line=dict(color='#EF553B', width=2), marker=dict(size=4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['depth_cost_final'], mode='lines+markers',
                             name='Depth Final', line=dict(color='#00CC96', width=2), marker=dict(size=4)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['depth_reduction_pct'], mode='lines',
                             name='Reduction %', fill='tozeroy', line=dict(color='#636EFA', width=2)), row=2, col=1, secondary_y=False)
    fig.add_trace(go.Scatter(x=df['frame_id'], y=df['num_depth_factors'], mode='lines',
                             name='# Factors', line=dict(color='#FFA15A', width=2, dash='dot')), row=2, col=1, secondary_y=True)
    
    has_depth = df['num_depth_factors'].sum() > 0
    if has_depth:
        fig.update_yaxes(type="log", title_text="Cost (log scale)", row=1, col=1)
    fig.update_yaxes(title_text="Reduction %", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="# Factors", row=2, col=1, secondary_y=True)
    fig.update_layout(height=600, title_text=f"<b>Depth Prior Factor Analysis{title_suffix}</b>", title_x=0.5,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), hovermode='x unified')
    return fig

def create_comparison_figure(df1, df2, name1, name2):
    """Compare two datasets side by side."""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(f'Total Cost - {name1}', f'Total Cost - {name2}',
                        f'Visual Cost - {name1}', f'Visual Cost - {name2}'),
        vertical_spacing=0.1, horizontal_spacing=0.08
    )
    
    # Total cost
    fig.add_trace(go.Scatter(x=df1['frame_id'], y=df1['total_cost_init'], name='Initial', line=dict(color='#EF553B', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df1['frame_id'], y=df1['total_cost_final'], name='Final', line=dict(color='#00CC96', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df2['frame_id'], y=df2['total_cost_init'], name='Initial', line=dict(color='#EF553B', width=2), showlegend=False), row=1, col=2)
    fig.add_trace(go.Scatter(x=df2['frame_id'], y=df2['total_cost_final'], name='Final', line=dict(color='#00CC96', width=2), showlegend=False), row=1, col=2)
    
    # Visual cost
    fig.add_trace(go.Scatter(x=df1['frame_id'], y=df1['visual_cost_init'], line=dict(color='#EF553B', width=2), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=df1['frame_id'], y=df1['visual_cost_final'], line=dict(color='#00CC96', width=2), showlegend=False), row=2, col=1)
    fig.add_trace(go.Scatter(x=df2['frame_id'], y=df2['visual_cost_init'], line=dict(color='#EF553B', width=2), showlegend=False), row=2, col=2)
    fig.add_trace(go.Scatter(x=df2['frame_id'], y=df2['visual_cost_final'], line=dict(color='#00CC96', width=2), showlegend=False), row=2, col=2)
    
    for row in [1, 2]:
        for col in [1, 2]:
            fig.update_yaxes(type="log", row=row, col=col)
    
    fig.update_layout(height=700, title_text=f"<b>Comparison: {name1} vs {name2}</b>", title_x=0.5,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5), hovermode='x unified')
    return fig

def compute_summary_stats(df):
    """Compute summary statistics for a dataset."""
    df = df.copy()
    df['total_visual_factors'] = df['num_visual_mono_factors'] + df['num_visual_stereo_factors'] + df['num_visual_one_frame_factors']
    
    return {
        'frames': len(df),
        'solver_time_avg': df['solver_time_ms'].mean(),
        'iterations_avg': df['iterations'].mean(),
        'total_cost_init_med': df['total_cost_init'].median(),
        'total_cost_final_med': df['total_cost_final'].median(),
        'total_reduction_avg': df['total_reduction_pct'].mean(),
        'visual_cost_init_med': df['visual_cost_init'].median(),
        'visual_cost_final_med': df['visual_cost_final'].median(),
        'visual_reduction_avg': df['visual_reduction_pct'].mean(),
        'imu_cost_init_med': df['imu_cost_init'].median(),
        'imu_cost_final_med': df['imu_cost_final'].median(),
        'imu_reduction_avg': df['imu_reduction_pct'].mean(),
        'depth_cost_init_med': df['depth_cost_init'].median(),
        'depth_cost_final_med': df['depth_cost_final'].median(),
        'depth_reduction_avg': df['depth_reduction_pct'].mean(),
        'num_features_avg': df['num_features'].mean(),
        'num_depth_factors_avg': df['num_depth_factors'].mean(),
    }

def generate_interactive_compare_page(csv_files, output_dir, all_data):
    """Generate an interactive comparison page with JavaScript-based selection."""
    
    # Prepare data as JSON for JavaScript
    import json
    
    datasets_json = {}
    for name, df in all_data.items():
        df_copy = df.copy()
        df_copy['total_visual_factors'] = df_copy['num_visual_mono_factors'] + df_copy['num_visual_stereo_factors'] + df_copy['num_visual_one_frame_factors']
        datasets_json[name] = {
            'frame_id': df_copy['frame_id'].tolist(),
            'total_cost_init': df_copy['total_cost_init'].tolist(),
            'total_cost_final': df_copy['total_cost_final'].tolist(),
            'total_reduction_pct': df_copy['total_reduction_pct'].tolist(),
            'visual_cost_init': df_copy['visual_cost_init'].tolist(),
            'visual_cost_final': df_copy['visual_cost_final'].tolist(),
            'visual_reduction_pct': df_copy['visual_reduction_pct'].tolist(),
            'imu_cost_init': df_copy['imu_cost_init'].tolist(),
            'imu_cost_final': df_copy['imu_cost_final'].tolist(),
            'imu_reduction_pct': df_copy['imu_reduction_pct'].tolist(),
            'depth_cost_init': df_copy['depth_cost_init'].tolist(),
            'depth_cost_final': df_copy['depth_cost_final'].tolist(),
            'depth_reduction_pct': df_copy['depth_reduction_pct'].tolist(),
            'margin_cost_init': df_copy['margin_cost_init'].tolist(),
            'margin_cost_final': df_copy['margin_cost_final'].tolist(),
            'margin_reduction_pct': df_copy['margin_reduction_pct'].tolist(),
            'num_depth_factors': df_copy['num_depth_factors'].tolist(),
            'total_visual_factors': df_copy['total_visual_factors'].tolist(),
            'num_imu_factors': df_copy['num_imu_factors'].tolist(),
            'num_margin_factors': df_copy['num_margin_factors'].tolist(),
            'solver_time_ms': df_copy['solver_time_ms'].tolist(),
            'iterations': df_copy['iterations'].tolist(),
            'num_features': df_copy['num_features'].tolist(),
        }
    
    dataset_names = sorted(datasets_json.keys())
    
    # Create descriptions dictionary for JavaScript
    descriptions_json = {name: get_description(name) for name in dataset_names}
    
    # Create RMSE dictionary for JavaScript
    rmse_json = {name: get_rmse(name) for name in dataset_names}
    
    compare_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Interactive Comparison - VINS Optimization</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1600px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .nav {{ text-align: center; margin: 20px 0; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .nav a {{ margin: 0 15px; text-decoration: none; color: #3498db; font-weight: bold; }}
        .selectors {{ display: flex; justify-content: center; gap: 40px; margin: 20px 0; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); flex-wrap: wrap; }}
        .selector-group {{ display: flex; flex-direction: column; align-items: center; }}
        .selector-group label {{ font-weight: bold; margin-bottom: 8px; color: #2c3e50; font-size: 16px; }}
        .selector-group select {{ padding: 10px 15px; font-size: 14px; border: 2px solid #3498db; border-radius: 5px; min-width: 350px; cursor: pointer; }}
        .selector-group select:focus {{ outline: none; border-color: #2980b9; }}
        .selector-group .description {{ color: #7f8c8d; font-size: 12px; margin-top: 8px; font-style: italic; text-align: center; max-width: 350px; }}
        .rmse-value {{ color: #e74c3c; font-weight: bold; font-style: normal; }}
        .plot-type-selector {{ margin: 20px 0; text-align: center; }}
        .plot-type-selector button {{ padding: 12px 24px; margin: 5px; cursor: pointer; border: none; background: #ecf0f1; color: #2c3e50; border-radius: 5px; font-size: 14px; font-weight: bold; transition: all 0.2s; }}
        .plot-type-selector button:hover {{ background: #3498db; color: white; }}
        .plot-type-selector button.active {{ background: #2c3e50; color: white; }}
        .chart-container {{ background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .chart-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .chart {{ min-height: 400px; }}
        .stats-comparison {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin: 20px 0; }}
        .stats-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .stats-card h3 {{ margin: 0 0 5px 0; color: #2c3e50; text-align: center; }}
        .stats-card .card-desc {{ color: #7f8c8d; font-size: 11px; font-style: italic; text-align: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #3498db; }}
        .stats-card table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .stats-card td {{ padding: 6px 8px; border-bottom: 1px solid #eee; }}
        .stats-card td:first-child {{ color: #666; }}
        .stats-card td:last-child {{ text-align: right; font-family: monospace; }}
        .stats-card .section-header td {{ background: #34495e; color: white; font-weight: bold; padding: 8px; font-size: 12px; }}
        .better {{ color: #27ae60; font-weight: bold; }}
        .worse {{ color: #e74c3c; font-weight: bold; }}
        .delta-card {{ background: #e8f6f3; }}
        .delta-card .better {{ background: #d4edda; }}
        .delta-card .worse {{ background: #f8d7da; }}
    </style>
</head>
<body>
<div class="container">
    <h1>⚖️ Interactive Comparison Tool</h1>
    <div class="nav">
        <a href="index.html">📋 Overview</a> | <a href="compare.html">⚖️ Compare</a>
    </div>
    
    <div class="selectors">
        <div class="selector-group">
            <label>📁 File A (Base)</label>
            <select id="selectA" onchange="updateComparison()">
                {''.join([f'<option value="{name}">{name}</option>' for name in dataset_names])}
            </select>
            <div class="description" id="descA"></div>
        </div>
        <div class="selector-group">
            <label>📁 File B (Compare)</label>
            <select id="selectB" onchange="updateComparison()">
                {''.join([f'<option value="{name}" {"selected" if i==1 else ""}>{name}</option>' for i, name in enumerate(dataset_names)])}
            </select>
            <div class="description" id="descB"></div>
        </div>
    </div>
    
    <div class="plot-type-selector">
        <button onclick="setPlotType('total', this)">📊 Total Cost</button>
        <button onclick="setPlotType('visual', this)">📷 Visual</button>
        <button onclick="setPlotType('imu', this)">🔄 IMU</button>
        <button onclick="setPlotType('depth', this)">📏 Depth</button>
        <button class="active" onclick="setPlotType('all', this)">📈 All Plots</button>
    </div>
    
    <div id="summary-stats-container" class="stats-comparison"></div>
    
    <div id="charts-container"></div>
    
    <div id="detailed-stats-container" class="stats-comparison" style="margin-top: 40px;"></div>
</div>

<script>
const datasets = {json.dumps(datasets_json)};
const descriptions = {json.dumps(descriptions_json)};
const rmseData = {json.dumps(rmse_json)};
let currentPlotType = 'all';

function setPlotType(type, btn) {{
    currentPlotType = type;
    document.querySelectorAll('.plot-type-selector button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    updateComparison();
}}

function formatNum(n, decimals=4) {{
    if (Math.abs(n) > 1000 || (Math.abs(n) < 0.01 && n !== 0)) {{
        return n.toExponential(decimals);
    }}
    return n.toFixed(decimals);
}}

function mean(arr) {{
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}}

function updateComparison() {{
    const nameA = document.getElementById('selectA').value;
    const nameB = document.getElementById('selectB').value;
    const dataA = datasets[nameA];
    const dataB = datasets[nameB];
    
    // Update descriptions and RMSE
    const rmseA = rmseData[nameA];
    const rmseB = rmseData[nameB];
    const rmseStrA = rmseA !== null ? `<span class="rmse-value">📐 RMSE: ${{rmseA.toFixed(4)}}</span>` : '';
    const rmseStrB = rmseB !== null ? `<span class="rmse-value">📐 RMSE: ${{rmseB.toFixed(4)}}</span>` : '';
    document.getElementById('descA').innerHTML = (descriptions[nameA] || '') + (rmseStrA ? '<br>' + rmseStrA : '');
    document.getElementById('descB').innerHTML = (descriptions[nameB] || '') + (rmseStrB ? '<br>' + rmseStrB : '');
    
    // Update stats
    updateStats(nameA, nameB, dataA, dataB);
    
    // Update charts
    const container = document.getElementById('charts-container');
    container.innerHTML = '';
    
    if (currentPlotType === 'all') {{
        createComparisonPlot(container, dataA, dataB, nameA, nameB, 'total', 'Total Cost');
        createComparisonPlot(container, dataA, dataB, nameA, nameB, 'visual', 'Visual Cost');
        createComparisonPlot(container, dataA, dataB, nameA, nameB, 'imu', 'IMU Cost');
        createComparisonPlot(container, dataA, dataB, nameA, nameB, 'depth', 'Depth Cost');
    }} else {{
        createComparisonPlot(container, dataA, dataB, nameA, nameB, currentPlotType, 
            {{total: 'Total Cost', visual: 'Visual Cost', imu: 'IMU Cost', depth: 'Depth Cost'}}[currentPlotType]);
    }}
}}

function median(arr) {{
    const sorted = [...arr].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}}

function updateStats(nameA, nameB, dataA, dataB) {{
    const statsA = {{
        frames: dataA.frame_id.length,
        // Total costs
        total_init: median(dataA.total_cost_init),
        total_final: median(dataA.total_cost_final),
        total_reduction: mean(dataA.total_reduction_pct),
        // Visual costs
        visual_init: median(dataA.visual_cost_init),
        visual_final: median(dataA.visual_cost_final),
        visual_reduction: mean(dataA.visual_reduction_pct),
        // IMU costs
        imu_init: median(dataA.imu_cost_init),
        imu_final: median(dataA.imu_cost_final),
        imu_reduction: mean(dataA.imu_reduction_pct),
        // Depth costs
        depth_init: median(dataA.depth_cost_init),
        depth_final: median(dataA.depth_cost_final),
        depth_reduction: mean(dataA.depth_reduction_pct),
        // Margin costs
        margin_init: median(dataA.margin_cost_init),
        margin_final: median(dataA.margin_cost_final),
        margin_reduction: mean(dataA.margin_reduction_pct),
        // Solver metrics
        solver_time: mean(dataA.solver_time_ms),
        iterations: mean(dataA.iterations),
        // Factor counts
        visual_factors: mean(dataA.total_visual_factors),
        imu_factors: mean(dataA.num_imu_factors),
        depth_factors: mean(dataA.num_depth_factors),
        margin_factors: mean(dataA.num_margin_factors),
        features: mean(dataA.num_features),
    }};
    const statsB = {{
        frames: dataB.frame_id.length,
        // Total costs
        total_init: median(dataB.total_cost_init),
        total_final: median(dataB.total_cost_final),
        total_reduction: mean(dataB.total_reduction_pct),
        // Visual costs
        visual_init: median(dataB.visual_cost_init),
        visual_final: median(dataB.visual_cost_final),
        visual_reduction: mean(dataB.visual_reduction_pct),
        // IMU costs
        imu_init: median(dataB.imu_cost_init),
        imu_final: median(dataB.imu_cost_final),
        imu_reduction: mean(dataB.imu_reduction_pct),
        // Depth costs
        depth_init: median(dataB.depth_cost_init),
        depth_final: median(dataB.depth_cost_final),
        depth_reduction: mean(dataB.depth_reduction_pct),
        // Margin costs
        margin_init: median(dataB.margin_cost_init),
        margin_final: median(dataB.margin_cost_final),
        margin_reduction: mean(dataB.margin_reduction_pct),
        // Solver metrics
        solver_time: mean(dataB.solver_time_ms),
        iterations: mean(dataB.iterations),
        // Factor counts
        visual_factors: mean(dataB.total_visual_factors),
        imu_factors: mean(dataB.num_imu_factors),
        depth_factors: mean(dataB.num_depth_factors),
        margin_factors: mean(dataB.num_margin_factors),
        features: mean(dataB.num_features),
    }};
    
    function diffClass(a, b, lowerBetter=true) {{
        const pct = ((b - a) / Math.abs(a)) * 100;
        if (lowerBetter) {{
            return pct < -1 ? 'better' : (pct > 1 ? 'worse' : '');
        }} else {{
            return pct > 1 ? 'better' : (pct < -1 ? 'worse' : '');
        }}
    }}
    
    function diffStr(a, b, lowerBetter=true) {{
        const pct = ((b - a) / Math.abs(a)) * 100;
        const cls = diffClass(a, b, lowerBetter);
        const icon = cls === 'better' ? '🟢' : (cls === 'worse' ? '🔴' : '⚪');
        return `<span class="${{cls}}">${{icon}} ${{pct >= 0 ? '+' : ''}}${{pct.toFixed(1)}}%</span>`;
    }}
    
    // SIMPLE SUMMARY at the TOP (before plots)
    document.getElementById('summary-stats-container').innerHTML = `
        <div class="stats-card">
            <h3>📊 ${{nameA}}</h3>
            <table>
                <tr><td>Frames</td><td>${{statsA.frames}}</td></tr>
                <tr><td>Total Cost (Init)</td><td>${{formatNum(statsA.total_init)}}</td></tr>
                <tr><td>Total Cost (Final)</td><td>${{formatNum(statsA.total_final)}}</td></tr>
                <tr><td>Total Reduction</td><td>${{statsA.total_reduction.toFixed(2)}}%</td></tr>
                <tr><td>Visual Cost (Final)</td><td>${{formatNum(statsA.visual_final)}}</td></tr>
                <tr><td>IMU Cost (Final)</td><td>${{formatNum(statsA.imu_final)}}</td></tr>
                <tr><td>Depth Cost (Final)</td><td>${{formatNum(statsA.depth_final)}}</td></tr>
            </table>
        </div>
        <div class="stats-card">
            <h3>📊 ${{nameB}}</h3>
            <table>
                <tr><td>Frames</td><td>${{statsB.frames}}</td></tr>
                <tr><td>Total Cost (Init)</td><td>${{formatNum(statsB.total_init)}}</td></tr>
                <tr><td>Total Cost (Final)</td><td>${{formatNum(statsB.total_final)}}</td></tr>
                <tr><td>Total Reduction</td><td>${{statsB.total_reduction.toFixed(2)}}%</td></tr>
                <tr><td>Visual Cost (Final)</td><td>${{formatNum(statsB.visual_final)}}</td></tr>
                <tr><td>IMU Cost (Final)</td><td>${{formatNum(statsB.imu_final)}}</td></tr>
                <tr><td>Depth Cost (Final)</td><td>${{formatNum(statsB.depth_final)}}</td></tr>
            </table>
        </div>
        <div class="stats-card delta-card">
            <h3>Δ Change (B vs A)</h3>
            <table>
                <tr><td>Frames</td><td>-</td></tr>
                <tr><td>Total Cost (Init)</td><td>${{diffStr(statsA.total_init, statsB.total_init)}}</td></tr>
                <tr><td>Total Cost (Final)</td><td>${{diffStr(statsA.total_final, statsB.total_final)}}</td></tr>
                <tr><td>Total Reduction</td><td>${{diffStr(statsA.total_reduction, statsB.total_reduction, false)}}</td></tr>
                <tr><td>Visual Cost (Final)</td><td>${{diffStr(statsA.visual_final, statsB.visual_final)}}</td></tr>
                <tr><td>IMU Cost (Final)</td><td>${{diffStr(statsA.imu_final, statsB.imu_final)}}</td></tr>
                <tr><td>Depth Cost (Final)</td><td>${{diffStr(statsA.depth_final, statsB.depth_final)}}</td></tr>
            </table>
        </div>
    `;
    
    // DETAILED STATS at the BOTTOM (after plots)
    document.getElementById('detailed-stats-container').innerHTML = `
        <h2 style="grid-column: 1 / -1; color: #2c3e50; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📋 Detailed Statistics</h2>
        <div class="stats-card">
            <h3>📊 ${{nameA}} - Full Details</h3>
            <table>
                <tr class="section-header"><td colspan="2">📈 General</td></tr>
                <tr><td>Frames</td><td>${{statsA.frames}}</td></tr>
                <tr><td>Avg Solver Time</td><td>${{statsA.solver_time.toFixed(2)}} ms</td></tr>
                <tr><td>Avg Iterations</td><td>${{statsA.iterations.toFixed(1)}}</td></tr>
                
                <tr class="section-header"><td colspan="2">💰 Total Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsA.total_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsA.total_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsA.total_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">👁️ Visual Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsA.visual_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsA.visual_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsA.visual_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">🎯 IMU Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsA.imu_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsA.imu_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsA.imu_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">📏 Depth Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsA.depth_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsA.depth_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsA.depth_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">📦 Margin Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsA.margin_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsA.margin_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsA.margin_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">🔢 Factor Counts (avg)</td></tr>
                <tr><td>Visual Factors</td><td>${{statsA.visual_factors.toFixed(0)}}</td></tr>
                <tr><td>IMU Factors</td><td>${{statsA.imu_factors.toFixed(0)}}</td></tr>
                <tr><td>Depth Factors</td><td>${{statsA.depth_factors.toFixed(0)}}</td></tr>
                <tr><td>Margin Factors</td><td>${{statsA.margin_factors.toFixed(1)}}</td></tr>
                <tr><td>Features</td><td>${{statsA.features.toFixed(0)}}</td></tr>
            </table>
        </div>
        <div class="stats-card">
            <h3>📊 ${{nameB}} - Full Details</h3>
            <table>
                <tr class="section-header"><td colspan="2">📈 General</td></tr>
                <tr><td>Frames</td><td>${{statsB.frames}}</td></tr>
                <tr><td>Avg Solver Time</td><td>${{statsB.solver_time.toFixed(2)}} ms</td></tr>
                <tr><td>Avg Iterations</td><td>${{statsB.iterations.toFixed(1)}}</td></tr>
                
                <tr class="section-header"><td colspan="2">💰 Total Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsB.total_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsB.total_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsB.total_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">👁️ Visual Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsB.visual_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsB.visual_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsB.visual_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">🎯 IMU Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsB.imu_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsB.imu_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsB.imu_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">📏 Depth Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsB.depth_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsB.depth_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsB.depth_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">📦 Margin Cost</td></tr>
                <tr><td>Initial (med)</td><td>${{formatNum(statsB.margin_init)}}</td></tr>
                <tr><td>Final (med)</td><td>${{formatNum(statsB.margin_final)}}</td></tr>
                <tr><td>Reduction (avg)</td><td>${{statsB.margin_reduction.toFixed(2)}}%</td></tr>
                
                <tr class="section-header"><td colspan="2">🔢 Factor Counts (avg)</td></tr>
                <tr><td>Visual Factors</td><td>${{statsB.visual_factors.toFixed(0)}}</td></tr>
                <tr><td>IMU Factors</td><td>${{statsB.imu_factors.toFixed(0)}}</td></tr>
                <tr><td>Depth Factors</td><td>${{statsB.depth_factors.toFixed(0)}}</td></tr>
                <tr><td>Margin Factors</td><td>${{statsB.margin_factors.toFixed(1)}}</td></tr>
                <tr><td>Features</td><td>${{statsB.features.toFixed(0)}}</td></tr>
            </table>
        </div>
        <div class="stats-card delta-card">
            <h3>Δ Change (B vs A) - Full Details</h3>
            <table>
                <tr class="section-header"><td colspan="2">📈 General</td></tr>
                <tr><td>Frames</td><td>-</td></tr>
                <tr><td>Solver Time</td><td>${{diffStr(statsA.solver_time, statsB.solver_time)}}</td></tr>
                <tr><td>Iterations</td><td>${{diffStr(statsA.iterations, statsB.iterations)}}</td></tr>
                
                <tr class="section-header"><td colspan="2">💰 Total Cost</td></tr>
                <tr><td>Initial</td><td>${{diffStr(statsA.total_init, statsB.total_init)}}</td></tr>
                <tr><td>Final</td><td>${{diffStr(statsA.total_final, statsB.total_final)}}</td></tr>
                <tr><td>Reduction</td><td>${{diffStr(statsA.total_reduction, statsB.total_reduction, false)}}</td></tr>
                
                <tr class="section-header"><td colspan="2">👁️ Visual Cost</td></tr>
                <tr><td>Initial</td><td>${{diffStr(statsA.visual_init, statsB.visual_init)}}</td></tr>
                <tr><td>Final</td><td>${{diffStr(statsA.visual_final, statsB.visual_final)}}</td></tr>
                <tr><td>Reduction</td><td>${{diffStr(statsA.visual_reduction, statsB.visual_reduction, false)}}</td></tr>
                
                <tr class="section-header"><td colspan="2">🎯 IMU Cost</td></tr>
                <tr><td>Initial</td><td>${{diffStr(statsA.imu_init, statsB.imu_init)}}</td></tr>
                <tr><td>Final</td><td>${{diffStr(statsA.imu_final, statsB.imu_final)}}</td></tr>
                <tr><td>Reduction</td><td>${{diffStr(statsA.imu_reduction, statsB.imu_reduction, false)}}</td></tr>
                
                <tr class="section-header"><td colspan="2">📏 Depth Cost</td></tr>
                <tr><td>Initial</td><td>${{diffStr(statsA.depth_init, statsB.depth_init)}}</td></tr>
                <tr><td>Final</td><td>${{diffStr(statsA.depth_final, statsB.depth_final)}}</td></tr>
                <tr><td>Reduction</td><td>${{diffStr(statsA.depth_reduction, statsB.depth_reduction, false)}}</td></tr>
                
                <tr class="section-header"><td colspan="2">📦 Margin Cost</td></tr>
                <tr><td>Initial</td><td>${{diffStr(statsA.margin_init, statsB.margin_init)}}</td></tr>
                <tr><td>Final</td><td>${{diffStr(statsA.margin_final, statsB.margin_final)}}</td></tr>
                <tr><td>Reduction</td><td>${{diffStr(statsA.margin_reduction, statsB.margin_reduction, false)}}</td></tr>
                
                <tr class="section-header"><td colspan="2">🔢 Factor Counts</td></tr>
                <tr><td>Visual Factors</td><td>${{diffStr(statsA.visual_factors, statsB.visual_factors, false)}}</td></tr>
                <tr><td>IMU Factors</td><td>${{diffStr(statsA.imu_factors, statsB.imu_factors, false)}}</td></tr>
                <tr><td>Depth Factors</td><td>${{diffStr(statsA.depth_factors, statsB.depth_factors, false)}}</td></tr>
                <tr><td>Margin Factors</td><td>${{diffStr(statsA.margin_factors, statsB.margin_factors, false)}}</td></tr>
                <tr><td>Features</td><td>${{diffStr(statsA.features, statsB.features, false)}}</td></tr>
            </table>
        </div>
    `;
}}

function createComparisonPlot(container, dataA, dataB, nameA, nameB, type, title) {{
    const chartDiv = document.createElement('div');
    chartDiv.className = 'chart-container';
    chartDiv.innerHTML = `<h3 style="text-align:center; color:#2c3e50;">${{title}}</h3><div class="chart-row"><div id="chart_${{type}}_A" class="chart"></div><div id="chart_${{type}}_B" class="chart"></div></div>`;
    container.appendChild(chartDiv);
    
    const fieldMap = {{
        total: ['total_cost_init', 'total_cost_final', 'total_reduction_pct'],
        visual: ['visual_cost_init', 'visual_cost_final', 'visual_reduction_pct'],
        imu: ['imu_cost_init', 'imu_cost_final', 'imu_reduction_pct'],
        depth: ['depth_cost_init', 'depth_cost_final', 'depth_reduction_pct'],
    }};
    
    const [initField, finalField, reductionField] = fieldMap[type];
    
    // Plot A
    const traceA1 = {{ x: dataA.frame_id, y: dataA[initField], name: 'Initial', line: {{color: '#EF553B', width: 2}} }};
    const traceA2 = {{ x: dataA.frame_id, y: dataA[finalField], name: 'Final', line: {{color: '#00CC96', width: 2}} }};
    
    Plotly.newPlot(`chart_${{type}}_A`, [traceA1, traceA2], {{
        title: nameA,
        yaxis: {{ type: 'log', title: 'Cost (log)' }},
        xaxis: {{ title: 'Frame ID' }},
        hovermode: 'x unified',
        margin: {{ t: 40 }},
    }});
    
    // Plot B  
    const traceB1 = {{ x: dataB.frame_id, y: dataB[initField], name: 'Initial', line: {{color: '#EF553B', width: 2}} }};
    const traceB2 = {{ x: dataB.frame_id, y: dataB[finalField], name: 'Final', line: {{color: '#00CC96', width: 2}} }};
    
    Plotly.newPlot(`chart_${{type}}_B`, [traceB1, traceB2], {{
        title: nameB,
        yaxis: {{ type: 'log', title: 'Cost (log)' }},
        xaxis: {{ title: 'Frame ID' }},
        hovermode: 'x unified',
        margin: {{ t: 40 }},
    }});
}}

// Initialize on load
document.addEventListener('DOMContentLoaded', updateComparison);
</script>
</body>
</html>"""
    
    compare_path = os.path.join(output_dir, 'compare.html')
    with open(compare_path, 'w') as f:
        f.write(compare_html)
    print(f"✅ Generated interactive comparison page: compare.html")

def generate_static_html(csv_files, output_dir, compare_pairs=None):
    """Generate static HTML dashboard."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate individual dataset pages
    dataset_pages = []
    all_stats = {}
    all_data = {}  # Store loaded data for comparison page
    
    for csv_path in csv_files:
        name = os.path.basename(csv_path).replace('.csv', '')
        print(f"📊 Processing: {name}")
        
        try:
            df = load_and_clean_data(csv_path)
        except Exception as e:
            print(f"   ⚠️ Error loading {csv_path}: {e}")
            continue
        
        # Store data for comparison page
        all_data[name] = df
        
        # Compute stats
        all_stats[name] = compute_summary_stats(df)
        
        # Create figures
        fig_total = create_total_cost_figure(df, f" - {name}")
        fig_visual = create_visual_cost_figure(df, f" - {name}")
        fig_imu = create_imu_cost_figure(df, f" - {name}")
        fig_depth = create_depth_cost_figure(df, f" - {name}")
        
        # Generate HTML page for this dataset
        page_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{name} - Optimization Analysis</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .nav {{ text-align: center; margin: 20px 0; padding: 15px; background: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .nav a {{ margin: 0 15px; text-decoration: none; color: #3498db; font-weight: bold; }}
        .nav a:hover {{ color: #2980b9; text-decoration: underline; }}
        .chart {{ background: white; margin: 20px 0; padding: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .stats {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .stats table {{ width: 100%; border-collapse: collapse; }}
        .stats th, .stats td {{ padding: 10px; text-align: left; border-bottom: 1px solid #eee; }}
        .stats th {{ background: #3498db; color: white; }}
    </style>
</head>
<body>
<div class="container">
    <h1>🔧 {name}</h1>
    <div class="nav">
        <a href="index.html">📋 Overview</a>
        {' | '.join([f'<a href="{os.path.basename(csv).replace(".csv", ".html")}">{os.path.basename(csv).replace(".csv", "")}</a>' for csv in csv_files[:10]])}
    </div>
    
    <div class="chart">
        {fig_total.to_html(full_html=False, include_plotlyjs='cdn')}
    </div>
    
    <div class="chart">
        {fig_visual.to_html(full_html=False, include_plotlyjs=False)}
    </div>
    
    <div class="chart">
        {fig_imu.to_html(full_html=False, include_plotlyjs=False)}
    </div>
    
    <div class="chart">
        {fig_depth.to_html(full_html=False, include_plotlyjs=False)}
    </div>
    
    <div class="stats">
        <h3>📋 Summary Statistics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Frames</td><td>{all_stats[name]['frames']}</td></tr>
            <tr><td>Avg Solver Time (ms)</td><td>{all_stats[name]['solver_time_avg']:.2f}</td></tr>
            <tr><td>Median Total Cost (Init)</td><td>{all_stats[name]['total_cost_init_med']:.4e}</td></tr>
            <tr><td>Median Total Cost (Final)</td><td>{all_stats[name]['total_cost_final_med']:.4e}</td></tr>
            <tr><td>Avg Total Reduction %</td><td>{all_stats[name]['total_reduction_avg']:.2f}%</td></tr>
            <tr><td>Median Visual Cost (Final)</td><td>{all_stats[name]['visual_cost_final_med']:.4e}</td></tr>
            <tr><td>Avg Depth Factors</td><td>{all_stats[name]['num_depth_factors_avg']:.1f}</td></tr>
        </table>
    </div>
</div>
</body>
</html>"""
        
        page_path = os.path.join(output_dir, f"{name}.html")
        with open(page_path, 'w') as f:
            f.write(page_html)
        
        dataset_pages.append({'name': name, 'path': f"{name}.html", 'stats': all_stats[name]})
    
    # Generate comparison pages if requested
    comparison_pages = []
    if compare_pairs:
        for csv1, csv2 in compare_pairs:
            name1 = os.path.basename(csv1).replace('.csv', '')
            name2 = os.path.basename(csv2).replace('.csv', '')
            print(f"🔄 Generating comparison: {name1} vs {name2}")
            
            try:
                df1 = load_and_clean_data(csv1)
                df2 = load_and_clean_data(csv2)
            except:
                continue
            
            fig_compare = create_comparison_figure(df1, df2, name1, name2)
            
            compare_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Compare: {name1} vs {name2}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; text-align: center; }}
        .nav {{ text-align: center; margin: 20px 0; padding: 15px; background: white; border-radius: 8px; }}
        .nav a {{ margin: 0 15px; text-decoration: none; color: #3498db; font-weight: bold; }}
        .chart {{ background: white; margin: 20px 0; padding: 15px; border-radius: 8px; }}
    </style>
</head>
<body>
<div class="container">
    <h1>⚖️ {name1} vs {name2}</h1>
    <div class="nav"><a href="index.html">← Back to Overview</a></div>
    <div class="chart">
        {fig_compare.to_html(full_html=False, include_plotlyjs='cdn')}
    </div>
</div>
</body>
</html>"""
            
            compare_path = os.path.join(output_dir, f"compare_{name1}_vs_{name2}.html")
            with open(compare_path, 'w') as f:
                f.write(compare_html)
            comparison_pages.append({'name': f"{name1} vs {name2}", 'path': f"compare_{name1}_vs_{name2}.html"})
    
    # Generate index page
    index_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>VINS-Fusion Optimization Dashboard</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #2c3e50; text-align: center; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; }}
        .card-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: transform 0.2s; }}
        .card:hover {{ transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0,0,0,0.15); }}
        .card h3 {{ margin: 0 0 10px 0; color: #2c3e50; }}
        .card .description {{ color: #7f8c8d; font-size: 12px; margin-bottom: 12px; line-height: 1.4; font-style: italic; border-left: 3px solid #3498db; padding-left: 10px; }}
        .card a {{ color: #3498db; text-decoration: none; font-weight: bold; }}
        .card a:hover {{ text-decoration: underline; }}
        .card .stat {{ color: #666; font-size: 14px; margin: 5px 0; }}
        .card .stat.rmse {{ color: #e74c3c; font-weight: bold; font-size: 15px; margin: 8px 0; }}
        .section {{ margin: 40px 0; }}
        .section h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .compare-section {{ background: #e8f4f8; padding: 20px; border-radius: 8px; }}
        .compare-button {{ display: block; text-align: center; padding: 20px 40px; background: linear-gradient(135deg, #3498db, #2980b9); color: white; text-decoration: none; font-size: 20px; font-weight: bold; border-radius: 10px; margin: 20px auto; max-width: 400px; box-shadow: 0 4px 15px rgba(52,152,219,0.4); transition: all 0.3s; }}
        .compare-button:hover {{ transform: translateY(-3px); box-shadow: 0 6px 20px rgba(52,152,219,0.5); }}
        .detailed-stats {{ width: 100%; border-collapse: collapse; font-size: 12px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .detailed-stats th {{ background: #34495e; color: white; padding: 10px 8px; text-align: left; position: sticky; top: 0; }}
        .detailed-stats td {{ padding: 8px; border-bottom: 1px solid #eee; font-family: monospace; }}
        .detailed-stats tr:hover {{ background: #f5f9fc; }}
        .detailed-stats td:first-child {{ font-family: 'Segoe UI', Arial, sans-serif; font-weight: bold; }}
        .detailed-stats a {{ color: #3498db; text-decoration: none; }}
        .detailed-stats a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
<div class="container">
    <h1>🔧 VINS-Fusion Optimization Dashboard</h1>
    <p class="subtitle">You may compare baselines with variants below!:</p>
    
    <a href="compare.html" class="compare-button">⚖️ Interactive Comparison Tool</a>
    
    <div class="section">
        <h2>📊 Datasets ({len(dataset_pages)})</h2>
        <div class="card-grid">
"""
    
    for page in dataset_pages:
        stats = page['stats']
        description = get_description(page['name'])
        rmse = get_rmse(page['name'])
        rmse_html = f'<div class="stat rmse">📐 RMSE: {rmse:.4f}</div>' if rmse is not None else ''
        index_html += f"""
            <div class="card">
                <h3><a href="{page['path']}">{page['name']}</a></h3>
                <div class="description">{description}</div>
                {rmse_html}
                <div class="stat">📈 Frames: {stats['frames']}</div>
                <div class="stat">⏱️ Avg Solver: {stats['solver_time_avg']:.1f}ms</div>
                <div class="stat">📉 Avg Reduction: {stats['total_reduction_avg']:.1f}%</div>
                <div class="stat">📏 Depth Factors: {stats['num_depth_factors_avg']:.0f}</div>
            </div>
"""
    
    index_html += """
        </div>
    </div>
"""
    
    if comparison_pages:
        index_html += """
    <div class="section">
        <h2>⚖️ Comparisons</h2>
        <div class="compare-section">
            <ul>
"""
        for comp in comparison_pages:
            index_html += f'                <li><a href="{comp["path"]}">{comp["name"]}</a></li>\n'
        index_html += """
            </ul>
        </div>
    </div>
"""
    
    # Add detailed statistics section at the bottom
    index_html += """
    <div class="section">
        <h2>📋 Detailed Statistics</h2>
        <p style="color: #666; margin-bottom: 20px;">Comprehensive statistics for all datasets. Cost values are medians (robust to outliers), reductions are averages.</p>
        <div style="overflow-x: auto;">
            <table class="detailed-stats">
                <thead>
                    <tr>
                        <th>Dataset</th>
                        <th>Frames</th>
                        <th>Solver (ms)</th>
                        <th>Iterations</th>
                        <th>Total Init</th>
                        <th>Total Final</th>
                        <th>Total Red %</th>
                        <th>Visual Init</th>
                        <th>Visual Final</th>
                        <th>Visual Red %</th>
                        <th>IMU Init</th>
                        <th>IMU Final</th>
                        <th>Depth Factors</th>
                        <th>Features</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for page in dataset_pages:
        stats = page['stats']
        name = page['name']
        index_html += f"""                    <tr>
                        <td><a href="{page['path']}">{name}</a></td>
                        <td>{stats['frames']}</td>
                        <td>{stats['solver_time_avg']:.1f}</td>
                        <td>{stats['iterations_avg']:.1f}</td>
                        <td>{stats['total_cost_init_med']:.2e}</td>
                        <td>{stats['total_cost_final_med']:.2e}</td>
                        <td>{stats['total_reduction_avg']:.1f}%</td>
                        <td>{stats['visual_cost_init_med']:.2e}</td>
                        <td>{stats['visual_cost_final_med']:.2e}</td>
                        <td>{stats['visual_reduction_avg']:.1f}%</td>
                        <td>{stats['imu_cost_init_med']:.2e}</td>
                        <td>{stats['imu_cost_final_med']:.2e}</td>
                        <td>{stats['num_depth_factors_avg']:.0f}</td>
                        <td>{stats['num_features_avg']:.0f}</td>
                    </tr>
"""
    
    index_html += """                </tbody>
            </table>
        </div>
    </div>
"""
    
    index_html += """
</div>
</body>
</html>"""
    
    index_path = os.path.join(output_dir, 'index.html')
    with open(index_path, 'w') as f:
        f.write(index_html)
    
    # Generate interactive comparison page
    if all_data:
        generate_interactive_compare_page(csv_files, output_dir, all_data)
    
    print(f"\n✅ Static dashboard generated in: {output_dir}")
    print(f"   📄 Index: {index_path}")
    print(f"   📊 Dataset pages: {len(dataset_pages)}")
    print(f"   ⚖️ Interactive comparison: compare.html")
    
    return output_dir

def main():
    parser = argparse.ArgumentParser(description='Export Dash visualization to static HTML for GitHub Pages')
    parser.add_argument('--csv-dir', type=str, default='.',
                        help='Directory containing CSV files')
    parser.add_argument('--csv', type=str, nargs='*',
                        help='Specific CSV files to include (default: all in csv-dir)')
    parser.add_argument('--output', type=str, default='./static_dashboard',
                        help='Output directory for static HTML files')
    parser.add_argument('--compare', type=str, nargs='*',
                        help='Pairs to compare (format: file1.csv:file2.csv)')
    parser.add_argument('--pattern', type=str, default='P*.csv',
                        help='Glob pattern for CSV files (default: P*.csv)')
    parser.add_argument('--rmse', type=str, default=None,
                        help='Path to RMSE results CSV file')
    
    args = parser.parse_args()
    
    # Load RMSE data
    if args.rmse:
        load_rmse_data(args.rmse)
    else:
        load_rmse_data()
    
    # Find CSV files
    if args.csv:
        csv_files = args.csv
    else:
        csv_files = sorted(glob.glob(os.path.join(args.csv_dir, args.pattern)))
    
    if not csv_files:
        print(f"❌ No CSV files found in {args.csv_dir}")
        return
    
    print(f"📁 Found {len(csv_files)} CSV files")
    
    # Parse comparison pairs
    compare_pairs = []
    if args.compare:
        for pair in args.compare:
            if ':' in pair:
                f1, f2 = pair.split(':', 1)
                # Resolve paths
                if not os.path.isabs(f1):
                    f1 = os.path.join(args.csv_dir, f1)
                if not os.path.isabs(f2):
                    f2 = os.path.join(args.csv_dir, f2)
                compare_pairs.append((f1, f2))
    
    # Generate static HTML
    generate_static_html(csv_files, args.output, compare_pairs)
    
    print(f"\n🚀 To preview locally:")
    print(f"   cd {args.output} && python3 -m http.server 8080")
    print(f"\n📤 To deploy to GitHub Pages:")
    print(f"   1. Create a GitHub repo")
    print(f"   2. Copy contents of {args.output} to repo")
    print(f"   3. Enable GitHub Pages in repo settings")

if __name__ == '__main__':
    main()
