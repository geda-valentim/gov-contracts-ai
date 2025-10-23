#!/bin/bash
# Set persistent password for Simple Auth Manager

PASSWORD_FILE="${AIRFLOW_HOME}/simple_auth_manager_passwords.json.generated"
CUSTOM_PASSWORD="${AIRFLOW_PASSWORD:-airflow}"

# Create password file with consistent password
echo "{\"airflow\": \"${CUSTOM_PASSWORD}\"}" > "${PASSWORD_FILE}"
chmod 666 "${PASSWORD_FILE}"

echo "Password file created at ${PASSWORD_FILE} with password: ${CUSTOM_PASSWORD}"

# Execute the original entrypoint
exec /entrypoint "$@"
