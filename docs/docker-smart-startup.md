# Smart Docker Startup

## Overview

The project includes intelligent service detection for **PostgreSQL, Redis, MinIO, and OpenSearch** to avoid port conflicts when multiple projects share infrastructure.

## How It Works

The `make up-smart` command checks all core services and decides which to start:

### Detection Logic

For each service (PostgreSQL, Redis, MinIO, OpenSearch):

1. **Check if port is accessible**
   - Test configured port from `.env`

2. **Determine ownership**
   - If `govcontracts-[service]` container is running → Use it
   - If external service is available → Skip local, use external
   - If nothing available → Start local container

3. **Apply scaling**
   - External services available → `docker compose up -d --scale [service]=0`
   - No external services → `docker compose up -d` (start all)

## Usage

### Recommended: Smart Startup

```bash
make up-smart
```

This command:
- ✅ Detects if MinIO is already running (local or external)
- ✅ Avoids port conflicts (9000, 9001)
- ✅ Uses existing MinIO if available
- ✅ Starts local MinIO only if needed

### Manual Check

Check all services availability:

```bash
make check-services
```

Output:
```
🔍 Checking services availability...

MinIO:
  ✅ Available at localhost:9000

PostgreSQL:
  ✅ Available at localhost:5433

Redis:
  ✅ Available at localhost:6380
```

Check only MinIO:

```bash
make check-minio
```

### Traditional Startup (Not Recommended)

```bash
make up  # or docker compose up -d
```

⚠️ **Warning**: May cause port conflicts if MinIO is already running elsewhere.

## Common Scenarios

### Scenario 1: Using Shared Infrastructure

If you have shared containers running (from another project):

```bash
# Shared services running
docker ps --filter "name=shared"
# shared-minio    (ports 9000-9001)
# shared-redis    (port 6379)
# shared-postgres (port 5432)

# Start services
make up-smart
```

**Output**:
```
❌ PostgreSQL: Not available - will start local
❌ Redis: Not available - will start local
✅ MinIO: External service available (localhost:9000) - will skip local
❌ OpenSearch: Not available - will start local

🐳 Starting services...
   Scale options:   --scale minio=0 --scale minio-init=0
```

**Result**:
- Uses `shared-minio` ✅
- Starts local `govcontracts-postgres` (port 5433) ✅
- Starts local `govcontracts-redis` (port 6380) ✅
- Starts local `govcontracts-opensearch` ✅

### Scenario 2: Fresh Installation

No MinIO running on the machine:

```bash
make up-smart
```

**Result**: Starts all services including local `govcontracts-minio`

### Scenario 3: Remote MinIO

Using remote MinIO server:

```bash
# .env configuration
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key

# Start services
make up-smart
```

**Result**: Connects to remote MinIO, skips local container

## Configuration

### Environment Variables (.env)

```bash
# MinIO Endpoint (can be localhost, container name, or remote)
MINIO_ENDPOINT=localhost:9000

# Credentials
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
```

### Docker Compose Behavior

The smart startup uses:

```bash
# When external MinIO is available
docker compose up -d --scale minio=0 --scale minio-init=0

# When no MinIO is available
docker compose up -d
```

The `--scale minio=0` option:
- ✅ Keeps service definition (no dependency errors)
- ✅ Doesn't start the container
- ✅ Allows other services (MLflow, Airflow) to work normally

## Troubleshooting

### Port Conflict Error

```
Error: Bind for 0.0.0.0:9000 failed: port is already allocated
```

**Solution**: Use `make up-smart` instead of `make up`

### MinIO Connection Refused

**Check MinIO status**:
```bash
docker ps --filter "name=minio"
nc -zv localhost 9000
```

**Verify credentials**:
```bash
# Test with MinIO client
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local
```

### Services Can't Connect to MinIO

**Check Docker network**:
```bash
docker network inspect govcontracts-network
```

**For external MinIO**: Ensure services can reach the endpoint
```bash
# From inside a container
docker exec govcontracts-mlflow curl http://minio:9000/minio/health/live
```

**For localhost MinIO**: Use `MINIO_ENDPOINT_DOCKER` for container-to-container communication
```bash
# .env
MINIO_ENDPOINT=localhost:9000           # For host access
MINIO_ENDPOINT_DOCKER=minio:9000        # For container access
```

## Technical Details

### Detection Logic (Makefile)

```makefile
check-minio:
    # Extract endpoint from .env
    ENDPOINT=$(grep "^MINIO_ENDPOINT=" .env | cut -d= -f2)
    HOST=$(echo $ENDPOINT | cut -d: -f1)
    PORT=$(echo $ENDPOINT | cut -d: -f2)

    # Test port connectivity
    if nc -z -w2 $HOST $PORT; then
        echo "✅ MinIO is available"
    else
        echo "❌ MinIO not available"
    fi
```

### Smart Startup Logic

```makefile
up-smart:
    # Test MinIO availability
    if [MinIO is accessible]; then
        if [govcontracts-minio is running]; then
            # Use local MinIO
            docker compose up -d
        else
            # Use external MinIO
            docker compose up -d --scale minio=0 --scale minio-init=0
        fi
    else
        # Start with local MinIO
        docker compose up -d
    fi
```

## Related Commands

| Command | Description |
|---------|-------------|
| `make up-smart` | Smart startup with full service detection |
| `make check-services` | Check all services availability |
| `make check-minio` | Check MinIO availability only |
| `make up` | Traditional startup (all services) |
| `make down` | Stop all services |
| `make logs` | View service logs |

## Best Practices

1. **Always use `make up-smart`** for development
2. **Configure `.env`** with correct MinIO endpoint
3. **Check logs** if services fail to connect: `docker compose logs mlflow airflow-worker`
4. **Use consistent credentials** across projects when sharing MinIO

## See Also

- [CLAUDE.md](../CLAUDE.md) - Development commands and patterns
- [docker-compose.yml](../docker-compose.yml) - Service definitions
- [Makefile](../Makefile) - Available commands
