# Querying the portal databases

The portal stores its state in two MySQL databases:

| Database     | Role                                   |
|--------------|----------------------------------------|
| `CLAS12OCR`  | Production                             |
| `CLAS12TEST` | Development / testing (the `--devel` target) |

You can talk to them two ways: directly with the raw MySQL commands, or through the `database.py`
wrapper in this directory. The wrapper reuses the portal's credential file and connection handling, so
it is the preferred entry point for scripts and ad hoc queries. The raw commands are documented
alongside because they are what you type once you are in a `mysql` shell, and they are what the `-q`
option ultimately runs.

## Prerequisites

- Run every command with the project interpreter: `~/venv/pymysql/bin/python3`.
- Network access to `jsubmit.jlab.org` is blocked inside the Bash sandbox. Run database commands with the
  sandbox disabled.
- Credentials come from `db_io/msql_conn.txt` by default (override with `-c FILE`). This file is private
  and is not committed.
- Run the commands from the repository root so `db_io/database.py` resolves.

## Connecting with the `mysql` client

`db_io/msql_conn.txt` is a standard MySQL option file with a `[client]` section (`user`, `password`,
`host`, `database`), so the `mysql` client can read it directly — no need to retype credentials or expose
the password on the command line:

```shell
mysql --defaults-extra-file=db_io/msql_conn.txt
```

This connects to the `host` and `database` named in the file (production `CLAS12OCR` by default). To open a
different database on the same server, name it on the command line:

```shell
mysql --defaults-extra-file=db_io/msql_conn.txt CLAS12TEST
```

The explicit form prompts for the password instead of reading the file (replace the user as needed):

```shell
mysql -h jsubmit.jlab.org -u ungaro -p CLAS12OCR
```

Once connected, the raw MySQL commands below run as-is at the `mysql>` prompt. As with `database.py`, the
sandbox blocks network access to `jsubmit.jlab.org`, so run the client with the sandbox disabled.

## `database.py` command-line options

```
-c, --credentials FILE   Credential file. Default: db_io/msql_conn.txt
-q, --query QUERY        SQL query or statement. Default: the recent-submissions query
-p, --params [P ...]     Positional SQL parameters, substituted for %s placeholders in order
--one                    Return only the first row (SELECT)
--execute                Treat the SQL as a non-SELECT statement (ALTER / INSERT / UPDATE / DELETE)
--database NAME          Database name, overriding the credential file (e.g. CLAS12TEST)
--output-format FMT      json (default), tsv, or job (formatted submission summary)
--indent N               JSON indentation. Default: 2
--no-autocommit          Disable autocommit
```

Run `~/venv/pymysql/bin/python3 db_io/database.py` with no arguments to print the help. With no `-q`, it
runs the default recent-submissions query (submissions from the last day).

## Raw MySQL commands and their `database.py` equivalents

`SELECT` statements need no special flag. Statements that change data or schema
(`ALTER` / `INSERT` / `UPDATE` / `DELETE` / `CREATE` / `DROP`) require `--execute`.

| Goal                         | Raw MySQL                               | `database.py` command                                                                 |
|------------------------------|-----------------------------------------|---------------------------------------------------------------------------------------|
| List tables                  | `SHOW TABLES;`                          | `database.py -q 'SHOW TABLES' --database=CLAS12OCR`                                    |
| Describe a table             | `DESCRIBE submissions;`                 | `database.py -q 'DESCRIBE submissions' --database=CLAS12OCR`                           |
| Show a table's columns       | `SHOW COLUMNS FROM submissions;`        | `database.py -q 'SHOW COLUMNS FROM submissions' --database=CLAS12OCR`                  |
| Show the CREATE statement    | `SHOW CREATE TABLE submissions;`        | `database.py -q 'SHOW CREATE TABLE submissions' --database=CLAS12OCR`                  |
| Select rows                  | `SELECT ... FROM submissions ...;`      | `database.py -q 'SELECT ... FROM submissions ...' --database=CLAS12OCR`                |
| Select one row               | `SELECT ... LIMIT 1;`                   | `database.py --one -q 'SELECT ...' --database=CLAS12OCR`                               |
| Count rows                   | `SELECT COUNT(*) FROM submissions;`     | `database.py -q 'SELECT COUNT(*) FROM submissions' --database=CLAS12OCR`               |
| Add / alter columns          | `ALTER TABLE submissions ADD ...;`      | `database.py --execute -q 'ALTER TABLE submissions ADD ...' --database=CLAS12OCR`      |
| Update rows                  | `UPDATE submissions SET ... WHERE ...;` | `database.py --execute -q 'UPDATE submissions SET ... WHERE ...' --database=CLAS12OCR` |

`SHOW DATABASES;` and the MySQL account listing below have no `database.py` shortcut beyond passing them
as a `-q` string; they are included here because they are common when inspecting the server.

## Examples

All examples assume you are at the repository root. Prefix with the project interpreter and run with the
sandbox disabled.

List the tables in production:

```shell
~/venv/pymysql/bin/python3 db_io/database.py -q 'SHOW TABLES' --database=CLAS12OCR
```

As of this writing the tables are `job_queue`, `owner_fairshare_snapshots`,
`owner_submission_snapshots`, `submissions`, and `users`.

Describe the `submissions` table (its columns are `user_submission_id`, `user_id`, `user`,
`client_time`, `scard`, `client_ip`, `server_time`, `pool_node`, `run_status`, `runscript_text`,
`clas12_condor_text`, `priority`, `done`, `completion_time`):

```shell
~/venv/pymysql/bin/python3 db_io/database.py -q 'DESCRIBE submissions' --database=CLAS12OCR
```

Select the most recent submissions, newest first:

```shell
~/venv/pymysql/bin/python3 db_io/database.py \
  -q 'SELECT user_submission_id, user, run_status FROM submissions ORDER BY user_submission_id DESC LIMIT 5' \
  --database=CLAS12OCR
```

Use `%s` placeholders with `-p` instead of interpolating values into the SQL string:

```shell
~/venv/pymysql/bin/python3 db_io/database.py \
  -q 'SELECT user_submission_id, run_status FROM submissions WHERE run_status = %s LIMIT 10' \
  -p 'Completed' --database=CLAS12OCR
```

Read a single column from one submission (handy for `runscript_text` or `scard`):

```shell
~/venv/pymysql/bin/python3 db_io/database.py --one \
  -q 'SELECT scard FROM submissions WHERE user_submission_id = %s' -p 6697 --database=CLAS12OCR
```

Count completed submissions per day for a date range:

```shell
~/venv/pymysql/bin/python3 db_io/database.py --database=CLAS12OCR \
  -q "SELECT DATE(completion_time) AS day, COUNT(*) AS n, COALESCE(SUM(done),0) AS done \
      FROM submissions WHERE run_status='Completed' AND completion_time IS NOT NULL \
      GROUP BY DATE(completion_time) ORDER BY day"
```

Add columns (non-SELECT, so `--execute`):

```shell
~/venv/pymysql/bin/python3 db_io/database.py --execute \
  -q 'ALTER TABLE submissions ADD COLUMN done INT NULL, ADD COLUMN completion_time DATETIME NULL' \
  --database=CLAS12OCR
```

Update rows (non-SELECT, so `--execute`):

```shell
~/venv/pymysql/bin/python3 db_io/database.py --execute \
  -q 'UPDATE submissions SET run_status = %s WHERE user_submission_id = %s' \
  -p 'Completed' 6697 --database=CLAS12OCR
```

## Server-level commands

These run against the MySQL server rather than a single table. They have no `database.py` shortcut; pass
them to `-q` as needed.

List databases:

```sql
SHOW DATABASES;
```

List MySQL accounts:

```sql
SELECT User, Host FROM mysql.user ORDER BY User, Host;
```

## See also

- `db.md` — `CREATE TABLE` statements for the snapshot tables.
- The project `CLAUDE.md` — reference submission IDs for `CLAS12TEST` and operational notes.
