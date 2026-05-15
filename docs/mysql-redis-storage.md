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

## MySQL Setup

```sql
CREATE DATABASE a3_learning CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'a3'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON a3_learning.* TO 'a3'@'%';
FLUSH PRIVILEGES;
```

The application creates the `records` table automatically at startup. The table keeps the existing document-style record contract:

```text
kind + id -> JSON payload
```

This keeps the current API stable while moving the durable storage from SQLite to MySQL.

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
