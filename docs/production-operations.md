# Production database operations

The production settings require `DJANGO_DATABASE_URL` to point to PostgreSQL. Install PostgreSQL client tools on the operator workstation and use a restricted database account. Do not commit the connection URL or a database dump.

## Create a backup

In PowerShell, set the connection URL in the current session from your secrets manager, then create a timestamped custom-format dump:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
pg_dump --dbname $env:DJANGO_DATABASE_URL --format=custom --file "jaunpur-footwear-$stamp.dump"
```

Upload the dump to encrypted storage with access controls and retention. A successful `pg_dump` is not proof that recovery works; restore it periodically into a disposable database and run Django checks against that restored copy.

## Restore into a separate database

Create an empty, isolated recovery database first. Set `MAINTENANCE_DATABASE_URL` to the provider's maintenance database connection and `RECOVERY_DATABASE_URL` to the new recovery database connection, then restore:

```powershell
createdb --maintenance-db $env:MAINTENANCE_DATABASE_URL jaunpur_recovery
pg_restore --dbname $env:RECOVERY_DATABASE_URL --no-owner --clean --if-exists "jaunpur-footwear-backup.dump"
```

The database name passed to `createdb` must match the database encoded in `RECOVERY_DATABASE_URL`; adapt the command for the managed PostgreSQL provider. Never point a recovery test at the live production database. After restore, configure the application to use the recovery URL and run:

```powershell
python manage.py check --deploy
python manage.py showmigrations
```

Define backup frequency, retention, encryption, access, and recovery time objectives with the hosting provider before accepting customer orders.
