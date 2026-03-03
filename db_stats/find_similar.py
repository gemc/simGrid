#!/usr/bin/env python3

import argparse
import pymysql
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


def parse_generator_and_options(scard_text: str):
    """
    Extract generator and generator options from the scard text.

    We try to be robust to patterns like:
      generator: clasdis
      genOptions: --docker --q 1.5 20

    and also generatorOptions / generator_options, and the
    "clasdisgenOptions:" style seen in the DB dump.
    """
    if not isinstance(scard_text, str):
        scard_text = ""

    # 1) explicit "generator: <token>"
    gen_match = re.search(r'generator:\s*(\S+)', scard_text)
    generator = gen_match.group(1) if gen_match else ""

    # 2) options: generatorOptions / generator_options / genOptions
    genopt_match = re.search(
        r'(?:generatorOptions|generator_options|genOptions):\s*([^\r\n]+)',
        scard_text
    )
    gen_options = genopt_match.group(1).strip() if genopt_match else ""

    # 3) fallback: e.g. "clasdisgenOptions: ...", "..."
    if not generator:
        m = re.search(r'(\S+)\s*genOptions:', scard_text)
        if m:
            generator = m.group(1)

    return generator, gen_options


def estimate_jobs(generator: str, scard_text: str) -> int:
    """
    Estimate number of jobs for a submission.

    - If scard has 'jobs: N' => N
    - Else, if generator.startswith("/") => 10,000
    - Else => 1
    """
    if not isinstance(scard_text, str):
        scard_text = ""

    jobs_match = re.search(r'jobs:\s*(\d+)', scard_text)
    if jobs_match:
        return int(jobs_match.group(1))

    if isinstance(generator, str) and generator.startswith("/"):
        return 10000

    return 1


def get_lund_base(generator: str):
    """
    Look for /volatile/clas12/users/<username> or /volatile/clas12/<username>
    as directory segments, with no prefix/suffix on username.

    Returns:
        (base_path, username) or (None, None)

    Examples:
        /volatile/clas12/users/efuchey/... -> ("/volatile/clas12/efuchey", "efuchey")
        /volatile/clas12/efuchey/...      -> ("/volatile/clas12/efuchey", "efuchey")
    """
    if not isinstance(generator, str):
        return None, None

    # /volatile/clas12/users/<username>
    m = re.search(r'/volatile/clas12/users/([^/]+)', generator)
    if m:
        username = m.group(1)
        return f"/volatile/clas12/{username}", username

    # /volatile/clas12/<username>
    m = re.search(r'/volatile/clas12/([^/]+)', generator)
    if m:
        username = m.group(1)
        # Avoid treating "users" as a username
        if username == "users":
            return None, None
        return f"/volatile/clas12/{username}", username

    return None, None


def build_similarity_key(generator: str, gen_options: str):
    """
    Build a key representing the 'type' of submission.

    - If generator empty: skip (None, None, False).

    - If generator's path contains /volatile/clas12/users/<username> or
      /volatile/clas12/<username>:
        key = ('LUND_BASE', '/volatile/clas12/<username>'), username, is_path=True

    - Else if generator.startswith("/"):
        key = ('PATH_GEN', <directory>), None, is_path=True
        (we ignore options for these)

    - Else (non-path generators, e.g. "clasdis", "MCEGENpiN_radcorr"):
        key = ('GEN', generator, gen_options), None, is_path=False
    """
    if not generator:
        return None, None, False

    base, user = get_lund_base(generator)
    if base is not None:
        return ("LUND_BASE", base), user, True

    if generator.startswith("/"):
        last_slash = generator.rfind("/")
        if last_slash > 0:
            directory = generator[:last_slash]
        else:
            directory = generator
        return ("PATH_GEN", directory), None, True

    return ("GEN", generator, gen_options), None, False


def format_dt(dt):
    if dt is None:
        return "N/A"
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt)


def find_similar(start_date: str,
                 end_date: str,
                 filter_empty_options: bool = True,
                 debug: bool = False,
                 include_single_user_groups: bool = False):
    # Convert date strings to datetime
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt   = datetime.strptime(end_date, "%Y-%m-%d")

    # Connect to DB
    conn = pymysql.connect(**conn_params)
    cursor = conn.cursor()

    query = """
        SELECT user, client_time, scard
        FROM submissions
        WHERE client_time >= %s AND client_time <= %s;
    """
    cursor.execute(query, (start_dt, end_dt))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    total_rows = len(rows)
    if total_rows == 0:
        print("No submissions found in the given date range.")
        return

    # Debug counters
    skipped_no_generator = 0
    skipped_empty_options = 0
    kept_rows = 0

    # key -> list of submissions
    groups = defaultdict(list)

    for user, client_time, scard_text in rows:
        generator, gen_options = parse_generator_and_options(scard_text)

        key, lund_username, is_path = build_similarity_key(generator, gen_options)

        if key is None:
            skipped_no_generator += 1
            continue

        # Filter empty options ONLY for non-path generators
        if filter_empty_options and (not is_path) and gen_options == "":
            skipped_empty_options += 1
            continue

        jobs = estimate_jobs(generator, scard_text)

        groups[key].append({
            "user": user,
            "client_time": client_time,
            "jobs": jobs,
            "generator": generator,
            "gen_options": gen_options,
            "lund_username": lund_username,
        })
        kept_rows += 1

    repeating_groups = []

    for key, subs in groups.items():
        users_set = {s["user"] for s in subs}

        if key[0] == "LUND_BASE":
            # CLAS12 base directory: detect foreign users
            base_path = key[1]
            # get base owner
            m = re.match(r'/volatile/clas12/([^/]+)', base_path)
            base_owner = m.group(1) if m else None

            foreign_users = {u for u in users_set if u != base_owner}

            # We want ALL cases where someone uses another user's base
            if not foreign_users:
                continue

            # We keep this group even if only 1 submission, or only 1 distinct foreign user
            repeating_groups.append((key, subs, base_owner, foreign_users))
        else:
            # Non-LUND groups (GEN and PATH_GEN):
            # need at least 2 submissions of same type
            if len(subs) < 2:
                continue
            # and (by default) at least 2 distinct users,
            # unless the user explicitly asked to include single-user groups.
            if (not include_single_user_groups) and len(users_set) < 2:
                continue
            repeating_groups.append((key, subs, None, None))

    if debug:
        print(f"Total submissions in range:                      {total_rows}")
        print(f"  Skipped: no/missing generator or no match:     {skipped_no_generator}")
        print(f"  Skipped: empty gen options (non-path gens):    {skipped_empty_options}"
              f" (filter_empty_options={filter_empty_options})")
        print(f"  Kept after filtering:                          {kept_rows}")
        print(f"  Groups reported:                               {len(repeating_groups)}")
        print()

    if not repeating_groups:
        print("No repeated 'same' submission types found in this range (after filtering).")
        return

    # Sort groups by total jobs descending
    def group_total_jobs(item):
        _, subs, _, _ = item
        return sum(s["jobs"] for s in subs)

    repeating_groups.sort(key=group_total_jobs, reverse=True)

    print(f"\nFound {len(repeating_groups)} repeated submission types "
          f"between {start_date} and {end_date}.\n")
    print(f"Filter empty generator options (non-path gens only): {filter_empty_options}")
    print(f"Include single-user groups (non-LUND): {include_single_user_groups}\n")

    for idx, (key, subs, base_owner, foreign_users) in enumerate(repeating_groups, start=1):
        total_submissions = len(subs)
        total_jobs = sum(s["jobs"] for s in subs)
        users = [s["user"] for s in subs]
        unique_users = sorted(set(users))

        times = [s["client_time"] for s in subs]
        min_t = min(times) if times else None
        max_t = max(times) if times else None

        per_user = defaultdict(lambda: {"subs": 0, "jobs": 0, "min_t": None, "max_t": None})
        for s in subs:
            u = s["user"]
            per_user[u]["subs"] += 1
            per_user[u]["jobs"] += s["jobs"]
            t = s["client_time"]
            if per_user[u]["min_t"] is None or t < per_user[u]["min_t"]:
                per_user[u]["min_t"] = t
            if per_user[u]["max_t"] is None or t > per_user[u]["max_t"]:
                per_user[u]["max_t"] = t

        # Describe the key + collect full paths for LUND/PATH
        lund_paths = None

        if key[0] == "LUND_BASE":
            kind_desc = f"LUND base directory group: {key[1]}"
            genopt_desc = "(generator options ignored for this grouping)"
            lund_paths = sorted(set(s["generator"] for s in subs))
        elif key[0] == "PATH_GEN":
            kind_desc = f"Path-based generator directory group: {key[1]}"
            genopt_desc = "(generator options ignored for path generators)"
            lund_paths = sorted(set(s["generator"] for s in subs))
        else:  # "GEN"
            kind_desc = f"Generator: {key[1]}"
            genopt_desc = f"Generator options: {key[2]!r}"

        print("=" * 80)
        print(f"Group #{idx}")
        print(f"  {kind_desc}")
        print(f"  {genopt_desc}")
        print(f"  Submissions in group: {total_submissions}")
        print(f"  Estimated total jobs: {total_jobs:,}")
        print(f"  Distinct users: {len(unique_users)} -> {', '.join(str(u) for u in unique_users)}")

        # For LUND_BASE groups, explicitly show owner and foreign users
        if key[0] == "LUND_BASE":
            print(f"  LUND owner (from path): {base_owner}")
            print(f"  Users submitting from this base: {', '.join(unique_users)}")
            foreign_list = sorted(u for u in unique_users if u != base_owner)
            print(f"  Foreign users (using someone else's LUND base): "
                  f"{', '.join(foreign_list) if foreign_list else 'None'}")

        print(f"  Group date range: {format_dt(min_t)}  ->  {format_dt(max_t)}")

        if lund_paths:
            print("\n  Full LUND/path generators used in this group:")
            for p in lund_paths:
                print(f"      - {p}")

        print("\n  Per-user breakdown:")
        for u in sorted(per_user.keys()):
            info = per_user[u]
            print(f"    - {u}:")
            print(f"        submissions: {info['subs']}")
            print(f"        jobs:        {info['jobs']:,}")
            print(f"        first:       {format_dt(info['min_t'])}")
            print(f"        last:        {format_dt(info['max_t'])}")
        print()

    print("=" * 80)
    print("End of report.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Find and quantify 'similar' generator submissions in a date range."
    )

    parser.add_argument("--start_date", type=str, default="2024-06-01",
                        help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", type=str, default="2025-12-05",
                        help="End date in YYYY-MM-DD format (optional)")

    # Default: filter out submissions with empty generator options
    # for non-path generators only.
    parser.add_argument(
        "--no_filter_empty_options",
        action="store_true",
        help="Do NOT filter out submissions with empty generator options for non-path generators"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print filtering statistics and group counts"
    )

    parser.add_argument(
        "--include_single_user_groups",
        action="store_true",
        help="Also include groups where only one user is present (for non-LUND groups)"
    )

    args = parser.parse_args()

    filter_empty_options = not args.no_filter_empty_options

    find_similar(
        start_date=args.start_date,
        end_date=args.end_date,
        filter_empty_options=filter_empty_options,
        debug=args.debug,
        include_single_user_groups=args.include_single_user_groups
    )


if __name__ == "__main__":
    main()


