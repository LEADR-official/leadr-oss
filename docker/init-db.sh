#!/bin/bash
set -e

# This script runs on first container startup to create the application database and user
# Environment variables are provided by docker-compose from .env file

echo "Creating database and user from .env configuration..."

# Create the user if it doesn't exist (and if it's not the default postgres user)
if [ "$DB_USER" != "postgres" ]; then
    # Determine if we need password authentication
    if [ -z "$DB_PASSWORD" ]; then
        echo "Creating user '$DB_USER' without password (empty DB_PASSWORD)"
        CREATE_USER_CMD="CREATE USER \"$DB_USER\""
    else
        echo "Creating user '$DB_USER' with password"
        CREATE_USER_CMD="CREATE USER \"$DB_USER\" WITH PASSWORD '$DB_PASSWORD'"
    fi

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        -- Create user if it doesn't exist
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
                $CREATE_USER_CMD;
            END IF;
        END
        \$\$;

        -- Create database if it doesn't exist (and if different from default)
        SELECT 'CREATE DATABASE "$DB_NAME" OWNER "$DB_USER"'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

        -- Grant privileges
        GRANT ALL PRIVILEGES ON DATABASE "$DB_NAME" TO "$DB_USER";
EOSQL

    # If password is empty, configure trust authentication for this user
    if [ -z "$DB_PASSWORD" ]; then
        echo "Configuring trust authentication for user '$DB_USER' (no password)"
        # PREPEND trust authentication rule so it matches before generic scram-sha-256 rules
        # PostgreSQL evaluates pg_hba.conf from top to bottom, first match wins
        TRUST_RULE="host    $DB_NAME    $DB_USER    all    trust"
        TMP_FILE=$(mktemp)
        echo "$TRUST_RULE" > "$TMP_FILE"
        cat "$PGDATA/pg_hba.conf" >> "$TMP_FILE"
        mv "$TMP_FILE" "$PGDATA/pg_hba.conf"
        # Reload postgres configuration
        psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "SELECT pg_reload_conf();"
    fi

    echo "Database '$DB_NAME' and user '$DB_USER' created successfully"
else
    echo "Using default postgres user, skipping user creation"
fi
