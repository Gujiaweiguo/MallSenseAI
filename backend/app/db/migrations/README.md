# Alembic migrations

Run from the repository root:

```bash
alembic -c backend/app/db/alembic.ini upgrade head
```

Dry-run SQL output:

```bash
alembic -c backend/app/db/alembic.ini upgrade head --sql
```

The initial revision enables `pgvector` with `CREATE EXTENSION IF NOT EXISTS vector` on PostgreSQL and skips extension creation for SQLite development databases.
