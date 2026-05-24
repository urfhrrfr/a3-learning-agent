# MySQL + Redis Storage

The backend now supports MySQL as the durable record store and Redis as the optional cache layer.

## Roles

- MySQL stores durable application records: profiles, profile versions, jobs, generated resources, learning paths, assessments, and change logs.
- Redis caches short-lived snapshots such as generation job progress. Data in Redis is treated as rebuildable.
- SQLite remains a local fallback when `MYSQL_URL` and `DATABASE_URL` are empty.

## Environment

```env
MYSQL_URL=mysql+pymysql://a3:password@127.0.0.1:3306/a3_learning?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:6379/0
```

`DATABASE_URL` is also accepted for MySQL if `MYSQL_URL` is not set.

## Local MySQL Setup

The fastest local setup is Docker Compose:

```powershell
cd backend
docker compose -f docker-compose.storage.yml up -d
```

Then configure the backend:

```env
MYSQL_URL=mysql+pymysql://a3:123456@127.0.0.1:3306/a3_learning?charset=utf8mb4
REDIS_URL=redis://127.0.0.1:6379/0
```

If you already have MySQL installed locally, create the database and user manually instead:

```sql
CREATE DATABASE a3_learning CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'a3'@'127.0.0.1' IDENTIFIED BY 'password';
CREATE USER 'a3'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON a3_learning.* TO 'a3'@'127.0.0.1';
GRANT ALL PRIVILEGES ON a3_learning.* TO 'a3'@'localhost';
FLUSH PRIVILEGES;
```

On Windows with MySQL Server installed, run the SQL as an administrator user:

```powershell
mysql -u root -p
```

The same template is stored at `backend/scripts/init_mysql_local.sql`; replace `replace_with_a_strong_password` before running it:

```powershell
mysql -u root -p < scripts\init_mysql_local.sql
```

The application creates the `records` table automatically at startup. The table keeps the existing document-style record contract:

```text
kind + id -> JSON payload
```

This keeps the current API stable while moving the durable storage from SQLite to MySQL.

## SQLite Migration

Keep the existing SQLite database as the rollback source, then migrate all `records` rows into MySQL:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_mysql.py --dry-run
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_mysql.py
```

The migration script:

- reads `backend/data/app.db`
- validates every JSON payload
- creates a timestamped `app.db.bak-*` backup before writing
- creates the MySQL `records` table if needed
- upserts by `(kind, id)`
- verifies per-`kind` row counts after import

To verify later without writing:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_mysql.py --verify-only
```

## Redis Setup

Start Redis locally so `REDIS_URL=redis://127.0.0.1:6379/0` is reachable. The Docker Compose file above includes Redis with append-only persistence. Redis is a cache only; if it is down, the backend should keep running and `/api/health` will report `cache.available=false`.

## Health Check

`GET /api/health` includes:

```json
{
  "storage": {
    "backend": "mysql",
    "available": true,
    "reason": ""
  },
  "cache": {
    "enabled": true,
    "available": true,
    "reason": ""
  }
}
```

You can also check the configured services without starting Uvicorn:

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\check_mysql_redis.py
```

## Rollback

To return to SQLite for an emergency local demo, clear `MYSQL_URL` and restart the backend. The existing `backend/data/app.db` and its timestamped backups remain available.
