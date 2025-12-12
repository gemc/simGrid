#!/usr/bin/env python3

import argparse
import pymysql
import matplotlib.pyplot as plt
import re
from collections import defaultdict
from datetime import datetime


# Load DB credentials
conn_params = {}
with open("/Users/ungaro/msql_conn.txt", "r") as f:
    for line in f:
        if line.strip().startswith("[client]"):
            continue
        key, value = line.strip().split("=", 1)
        if value[0] == value[-1] and value.startswith(("'", '"')):
            value = value[1:-1]
        conn_params[key.strip()] = value.strip()


def format_date_label(dt):
    if dt is None:
        return "N/A"
    try:
        return dt.strftime("%Y-%m-%d")
    except AttributeError:
        return str(dt)[:10]


def plot_top_users(top_n=10, ignore_users=None, start_date=None, end_date=None):
    if ignore_users is None:
        ignore_users = []

    # Convert date strings → datetime
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt   = datetime.strptime(end_date, "%Y-%m-%d")

    # Connect to MySQL
    conn = pymysql.connect(**conn_params)
    cursor = conn.cursor()

    # Build WHERE clause
    where_clauses = ["client_time >= %s", "client_time <= %s"]
    params = [start_dt, end_dt]

    if ignore_users:
        placeholders = ",".join(["%s"] * len(ignore_users))
        where_clauses.append(f"user NOT IN ({placeholders})")
        params.extend(ignore_users)

    where_sql = "WHERE " + " AND ".join(where_clauses)

    # Fetch filtered submissions
    query = f"""
        SELECT user, client_time, scard
        FROM submissions
        {where_sql};
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()

    if not rows:
        print("No submissions found for the given filters.")
        cursor.close()
        conn.close()
        return

    # Aggregate jobs per user
    user_jobs = defaultdict(int)
    user_min_time = {}
    user_max_time = {}

    for user, client_time, scard_text in rows:

        if not isinstance(scard_text, str):
            scard_text = ""

        generator_match = re.search(r'generator:\s*(\S+)', scard_text)
        jobs_match = re.search(r'jobs:\s*(\d+)', scard_text)

        generator = generator_match.group(1) if generator_match else ""

        if jobs_match:
            jobs = int(jobs_match.group(1))
        else:
            # lund (path starting with "/")
            jobs = 20000 if generator.startswith("/") else 1

        user_jobs[user] += jobs

        # Track user date range
        if user not in user_min_time or client_time < user_min_time[user]:
            user_min_time[user] = client_time
        if user not in user_max_time or client_time > user_max_time[user]:
            user_max_time[user] = client_time

    cursor.close()
    conn.close()

    # Take top N users by job count
    sorted_users = sorted(user_jobs.items(), key=lambda kv: kv[1], reverse=True)
    top_users = sorted_users[:top_n]

    if not top_users:
        print("No users to display after filtering.")
        return

    users = [u for u, _ in top_users]
    jobs_counts = [user_jobs[u] for u in users]

    # Global min/max for plotted users
    # Show the requested filter range in the title
    start_label = start_dt.strftime("%Y-%m-%d")
    end_label = end_dt.strftime("%Y-%m-%d")

    # Plot
    fig, ax = plt.subplots(figsize=(12, 6))

    bars = ax.bar(users, jobs_counts, edgecolor="black")

    ax.set_xlabel("User")
    ax.set_ylabel("Number of Jobs")
    ax.set_xticklabels(users, rotation=45, ha="right")

    ax.set_title(
        f"Top {top_n} Users by Number of Jobs\n"
        f"Submissions from {start_label} to {end_label}"
    )

    # Total jobs across these users (inside the plot)
    total_top_jobs = sum(jobs_counts)
    ax.text(
        0.5, 0.90,  # relative coords (x=middle, y=90% of plot height)
        f"Total jobs (these users): {total_top_jobs:,}",
        ha="center",
        va="bottom",
        transform=ax.transAxes,
        fontsize=12,
        fontweight="bold"
    )

    # Labels above bars
    for bar, count in zip(bars, jobs_counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            count,
            f"{count:,}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold"
        )

    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(
        description="Plot top users by total number of jobs."
    )
    parser.add_argument("--top-n", type=int, default=12,
                        help="Number of top users to show.")
    parser.add_argument("--ignore-user", action="append", default=['ungaro'],
                        help="Usernames to ignore (can be repeated).")

    parser.add_argument("--start_date", type=str, default="2025-06-05",
                        help="Start date in YYYY-MM-DD format")

    parser.add_argument("--end_date", type=str, default="2025-12-05",
                        help="End date in YYYY-MM-DD format")

    args = parser.parse_args()

    plot_top_users(
        top_n=args.top_n,
        ignore_users=args.ignore_user,
        start_date=args.start_date,
        end_date=args.end_date
    )


if __name__ == "__main__":
    main()
