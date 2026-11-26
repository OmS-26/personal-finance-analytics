"""
Export the dashboard views to CSV for Tableau Public (which can't connect to MySQL directly),
then check the anomaly-detection view against the injected ground truth.

Usage:
  pip install -r requirements.txt
  python3 scripts/export_for_tableau.py --user root

You'll be prompted for the password. Connection settings can also come from the
MYSQL_HOST, MYSQL_USER and MYSQL_PASSWORD environment variables.
"""

import argparse
import csv
import getpass
import os
from pathlib import Path

import mysql.connector

ROOT = Path(__file__).resolve().parent.parent
EXPORTS = ROOT / "exports"
VIEWS = ["v_transactions_enriched", "v_flagged_transactions"]


def export_view(cursor, view):
    cursor.execute(f"SELECT * FROM {view}")
    path = EXPORTS / f"{view.removeprefix('v_')}.csv"
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(col[0] for col in cursor.description)
        rows = cursor.fetchall()
        writer.writerows(rows)
    print(f"Wrote {len(rows):>6} rows -> {path.relative_to(ROOT)}")


def evaluate_anomalies(cursor):
    truth_file = EXPORTS / "injected_anomalies.csv"
    if not truth_file.exists():
        print("No injected_anomalies.csv found; run generate_data.py first to evaluate.")
        return
    with open(truth_file) as f:
        truth = {int(row["transaction_id"]) for row in csv.DictReader(f)}

    cursor.execute("SELECT transaction_id FROM v_flagged_transactions")
    flagged = {row[0] for row in cursor.fetchall()}

    caught = flagged & truth
    false_positives = flagged - truth
    print("\nAnomaly detection check")
    print(f"  Injected anomalies:  {len(truth)}")
    print(f"  Caught:              {len(caught)} ({100 * len(caught) / len(truth):.0f}% recall)")
    print(f"  False positives:     {len(false_positives)}")
    if flagged:
        print(f"  Precision:           {100 * len(caught) / len(flagged):.0f}%")
    if truth - flagged:
        print(f"  Missed IDs:          {sorted(truth - flagged)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=os.getenv("MYSQL_HOST", "localhost"))
    parser.add_argument("--user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--password", default=os.getenv("MYSQL_PASSWORD"))
    args = parser.parse_args()
    if args.password is None:
        args.password = getpass.getpass(f"MySQL password for {args.user}: ")

    conn = mysql.connector.connect(host=args.host, user=args.user, password=args.password,
                                   database="finance_analytics")
    try:
        cursor = conn.cursor()
        EXPORTS.mkdir(exist_ok=True)
        for view in VIEWS:
            export_view(cursor, view)
        evaluate_anomalies(cursor)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
