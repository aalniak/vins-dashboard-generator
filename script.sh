./build_dashboard.sh \
    --csv-dir /media/SSD/tartan_csvs \
    --pattern "P200*.csv" \
    --rmse /media/SSD/tables/tartan_overall/results_table.csv \
    --output ./dashboard \
    --deploy \
    --repo-url https://github.com/aalniak/CSV_to_Diagnostics.git
