import pymysql
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.dates as mdates
import re
from collections import defaultdict
import argparse

# Virtual Environment

# python3 -m venv venv
# source venv/bin/activate
# python -m pip install PyMySQL matplotlib


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Aggregate job submissions over a given time period.")
parser.add_argument("--start_date", type=str, default="2022-09-01",
                    help="Start date in YYYY-MM-DD format")
parser.add_argument("--end_date", type=str, default="2025-09-01",
                    help="End date in YYYY-MM-DD format (optional)")
parser.add_argument("--aggregation", type=str, default="weeks",
                    choices=["days", "weeks", "months", "years"],
                    help="Time interval for aggregation")
parser.add_argument("--bin_years", type=float, default=1.0,
                    help="Bin size in years for overlay arrows (e.g. 1 = 1 year, 0.5 = 6 months)")
args = parser.parse_args()

# Convert input dates
start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
end_date = datetime.strptime(args.end_date, "%Y-%m-%d") if args.end_date else datetime.now()

# MySQL connection details
# Read MySQL connection details from file
conn_params = {}
with open("/Users/ungaro/msql_conn.txt", "r") as f:
	for line in f:
		if line.strip().startswith("[client]"):
			continue
		key, value = line.strip().split("=", 1)
		# remove quotes if present
		if value[0] == value[-1] and value.startswith(("'", '"')):
			value = value[1:-1]

		conn_params[key.strip()] = value.strip()

# Connect to MySQL database
conn = pymysql.connect(**conn_params)
cursor = conn.cursor()

# Query to fetch submission data
query = """
SELECT client_time, scard FROM submissions;
"""
cursor.execute(query)

data = cursor.fetchall()
cursor.close()
conn.close()

# Process data
time_stamps = []
number_of_jobs = []

for row in data:
	client_time, scard_text = row
	time_stamp = datetime.strptime(client_time, "%Y-%m-%d %H:%M:%S")

	# Ensure scard_text is a string
	if not isinstance(scard_text, str):
		scard_text = ""

	# Extract generator and jobs values
	generator_match = re.search(r'generator:\s*(\S+)', scard_text)
	jobs_match = re.search(r'jobs:\s*(\d+)', scard_text)

	generator = generator_match.group(1) if generator_match else ""
	jobs = int(jobs_match.group(1)) if jobs_match else 10000 if generator.startswith("/") else 1

	if start_date <= time_stamp <= end_date:
		time_stamps.append(time_stamp)
		number_of_jobs.append(jobs)

# Aggregate jobs
jobs_per_interval = defaultdict(int)

for ts, jobs in zip(time_stamps, number_of_jobs):
	if args.aggregation == "weeks":
		interval_start = start_date + timedelta(weeks=((ts - start_date).days // 7))
	elif args.aggregation == "days":
		interval_start = ts.replace(hour=0, minute=0, second=0, microsecond=0)
	elif args.aggregation == "months":
		interval_start = ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
	elif args.aggregation == "years":
		interval_start = ts.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

	jobs_per_interval[interval_start] += jobs

# Sort data for plotting
sorted_intervals = sorted(jobs_per_interval.keys())
sorted_counts = [jobs_per_interval[interval] for interval in sorted_intervals]

# Define spacing factor (0 means bars touch, 0.2 means 20% gap)
spacing_factor = 0.4

# Compute actual bar width based on aggregation
if args.aggregation == "weeks":
	bar_width = 6 * (1 - spacing_factor)
elif args.aggregation == "days":
	bar_width = 1 * (1 - spacing_factor)
elif args.aggregation == "months":
	bar_width = 25 * (1 - spacing_factor)  # Approximate month length
elif args.aggregation == "years":
	bar_width = 365 * (1 - spacing_factor)  # Approximate year length

# Plot the results with spacing
plt.figure(figsize=(12, 6))
plt.bar(sorted_intervals, sorted_counts, width=bar_width, edgecolor='black', alpha=0.75,
        align='center')

plt.xlabel("Time")
plt.ylabel("Number of Jobs")
plt.title(
	f"Number of Jobs Per {args.aggregation.capitalize()} from {start_date.date()} to {end_date.date()}")
plt.xticks(rotation=45)
plt.grid()

# Set y-axis limit with extra headroom for arrows/labels
max_y = max(sorted_counts) if sorted_counts else 1
plt.ylim(0, max_y * 1.3)

# Format x-axis based on aggregation
if args.aggregation == "weeks":
	plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
	plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
elif args.aggregation == "days":
	plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=7))
	plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
elif args.aggregation == "months":
	plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
	plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
elif args.aggregation == "years":
	plt.gca().xaxis.set_major_locator(mdates.YearLocator())
	plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

# --- Overlay bins with double-headed arrows and totals in millions ---
if sorted_intervals:
	# Approximate "year" as 365 days; scaled by bin_years
	bin_length = timedelta(days=int(365 * args.bin_years))

	current_bin_start = start_date
	y_arrow = max_y * 1.05
	y_text = max_y * 1.12

	while current_bin_start < end_date:
		current_bin_end = current_bin_start + bin_length

		# Sum jobs in this bin [current_bin_start, current_bin_end)
		bin_total = sum(
			count
			for t, count in zip(sorted_intervals, sorted_counts)
			if current_bin_start <= t < current_bin_end
		)

		if bin_total > 0:
			# Double-headed arrow along the x-axis at y_arrow
			plt.annotate(
				'',
				xy=(current_bin_end, y_arrow),
				xytext=(current_bin_start, y_arrow),
				arrowprops=dict(arrowstyle='<->', linewidth=1.5)
			)

			# Label in millions at the center of the bin
			bin_center = current_bin_start + (current_bin_end - current_bin_start) / 2
			plt.text(
				bin_center,
				y_text,
				f"{bin_total / 1_000_000:.1f}M",
				ha='center',
				va='bottom',
				fontsize=12,
				fontweight='bold'
			)

		current_bin_start = current_bin_end
# ---------------------------------------------------------------------

plt.show()
