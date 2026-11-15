"""Run from the project directory: python main.py --run."""
import argparse
import json
import sqlite3
import sys
import pandas as pd
from src.config import OUTPUT
from src.pipeline import run_pipeline
from src.database import DB_PATH, export_queries


def show_summary(summary):
    print(f"Rows: {summary['rows']:,}; wells: {summary['wells']}; active series: {summary['active_series']}")
    print(f"Missing hourly rows: {summary['missing_hourly_rows']:,} ({summary['missing_percent']:.2f}%)")
    print(f"Source-flagged rows: {summary['flagged_rows']:,}; SQL queries: {summary['sql_queries']}")
    print("Saved data/processed, outputs and sql. Start dashboard with: streamlit run app.py")


def execute():
    frame, summary = run_pipeline()
    try:
        from src.visualization import build_figures
    except ModuleNotFoundError as exc:
        if exc.name != "src.visualization":
            raise
        print("Visualization module is absent; tabular audit has completed.")
    else:
        print("7/7 Creating figures and the interactive Plotly chart...")
        build_figures(frame, summary)
    show_summary(summary)


def console_menu():
    while True:
        print("\n1 - Run ETL and audit\n2 - Show saved summary\n3 - Run SQL queries\n0 - Exit")
        choice = input("Choose: ").strip()
        if choice == "1":
            execute()
        elif choice == "2":
            show_summary(json.loads((OUTPUT / "summary.json").read_text(encoding="utf-8")))
        elif choice == "3":
            export_queries()
            print("12 query results saved in outputs/sql.")
        elif choice == "0":
            break
        else:
            print("Enter 0, 1, 2 or 3.")


def main():
    parser = argparse.ArgumentParser(description="Well-sensor data quality audit")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--run", action="store_true", help="Run all reproducible analyses (default)")
    group.add_argument("--sql", action="store_true", help="Re-export SQL query results from existing database")
    group.add_argument("--menu", action="store_true", help="Open interactive console menu")
    args = parser.parse_args()
    try:
        if args.menu:
            console_menu()
        elif args.sql:
            if not DB_PATH.exists():
                raise FileNotFoundError("Database missing. Run python main.py --run first.")
            export_queries()
            print("12 SQL result tables written to outputs/sql.")
        else:
            execute()
    except (FileNotFoundError, ValueError, OSError, sqlite3.DatabaseError) as exc:
        print(f"Project error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
