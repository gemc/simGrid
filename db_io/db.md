## owner_submission_snapshots table

Create with, within both databases:

```shell
CREATE TABLE owner_fairshare_snapshots (
    snapshot_id BIGINT NOT NULL AUTO_INCREMENT,
    database_name VARCHAR(64) NOT NULL,
    owner VARCHAR(128) NOT NULL,
    update_time DATETIME NOT NULL,
    payload_json LONGTEXT NOT NULL,
    PRIMARY KEY (snapshot_id),
    KEY idx_owner_db_time (owner, database_name, update_time)
);
```


To list account:

SELECT User, Host
FROM mysql.user
ORDER BY User, Host;

