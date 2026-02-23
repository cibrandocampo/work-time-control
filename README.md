# Work Time Control (WTC)

Time tracking and work hours management system with overtime calculation.

## Requirements

- Docker and Docker Compose
- Python 3.13+ (for local development)

## Quick Start

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f backend

# Frontend available at http://localhost:5173
# API available at http://localhost:8000
# Swagger documentation: http://localhost:8000/api/docs/
```

## Project Structure

```
work-time-control/
├── backend/                 # Django REST Framework API
│   └── src/
│       ├── apps/
│       │   ├── accounts/    # Authentication and users
│       │   ├── companies/   # Companies, locations and holidays
│       │   ├── core/        # Day types (DayType)
│       │   ├── workdays/    # Signings and work days
│       │   └── integrations/# External time manager integration
│       └── config/          # Django configuration
├── docs/                    # Documentation and examples
├── frontend/                # Vue 3 + PrimeVue frontend
└── docker-compose.yaml
```

## Main API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/token/` | POST | Obtain JWT token |
| `/api/auth/token/refresh/` | POST | Refresh token |
| `/api/me/` | GET | Current user information |

### Signings

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/signings/` | GET | List signings |
| `/api/signings/` | POST | Create signing (check-in) |
| `/api/signings/{id}/` | GET | Signing details |
| `/api/signings/{id}/checkout/` | POST | End signing (check-out) |
| `/api/signings/active/` | GET | Current active signing |
| `/api/signings/import/` | POST | Import signings from CSV |
| `/api/signings/export/` | GET | Export signings to CSV |
| `/api/integrations/sync/` | POST | Sync from external time manager |

### Work Days

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workdays/` | GET/POST | List/create work days |
| `/api/workdays/{id}/` | GET/PUT/DELETE | Manage work day |

### Summaries

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/summary/day/` | GET | Current day summary |
| `/api/summary/day/{date}/` | GET | Specific day summary |
| `/api/summary/period/` | GET | Monthly/yearly summary |

## CSV Import/Export

### Export Signings

```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/api/signings/export/?start_date=2026-01-01&end_date=2026-01-31" \
  -o signings.csv
```

**Parameters:**
- `start_date` (required): Start date (YYYY-MM-DD)
- `end_date` (required): End date (YYYY-MM-DD)

**Output format:**
```csv
date,start_time,end_time,duration_minutes,location,description
2026-01-15,2026-01-15 09:00:00+00:00,2026-01-15 18:00:00+00:00,540,Madrid HQ,Regular work
```

### Import Signings

```bash
curl -X POST -H "Authorization: Bearer TOKEN" \
  -F "file=@signings.csv" \
  "http://localhost:8000/api/signings/import/"
```

**Required CSV format:**
```csv
start_time,end_time,location_id,description
2026-02-01 09:00,2026-02-01 18:00,1,Office work
2026-02-02 08:30,2026-02-02 17:30,,Remote work
```

**Fields:**
| Field | Required | Format | Description |
|-------|----------|--------|-------------|
| `start_time` | Yes | `YYYY-MM-DD HH:MM` or ISO8601 | Check-in time |
| `end_time` | No | `YYYY-MM-DD HH:MM` or ISO8601 | Check-out time |
| `location_id` | No | Number | Location ID |
| `description` | No | Text | Description/notes |

**Success response:**
```json
{
  "imported": 25,
  "errors": []
}
```

**Error response:**
```json
{
  "imported": 0,
  "errors": [
    {"row": 3, "error": "Invalid date format in start_time"},
    {"row": 5, "error": "Location with id 99 not found"}
  ]
}
```

**Notes:**
- Import is atomic: if one row fails, nothing is imported
- A WorkDay is automatically created for each signing with a location
- See full example at [`docs/signings_import_example.csv`](docs/signings_import_example.csv)

## External Time Manager Integration

Sync signings from an external time management system.

### Configuration

1. Set the external time manager URL in your environment:
   ```bash
   EXTERNAL_TIME_MANAGER_URL=https://your-time-manager.example.com
   ```

2. Configure company external ID in Django admin (Companies > Company > External ID)

3. Configure user external ID in Django admin or via Settings page in the frontend

### Sync Endpoint

```bash
curl -X POST -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "external_api_token",
    "api_key": "external_api_key",
    "start_date": "2026-01-01",
    "end_date": "2026-01-31"
  }' \
  "http://localhost:8000/api/integrations/sync/"
```

**Request body:**
| Field | Required | Description |
|-------|----------|-------------|
| `token` | Yes | JWT token from external system |
| `api_key` | Yes | API key from external system |
| `start_date` | Yes | Start date (YYYY-MM-DD) |
| `end_date` | Yes | End date (YYYY-MM-DD) |

**Response:**
```json
{
  "imported": 43,
  "errors": []
}
```

**Notes:**
- Duplicate signings (same start_time) are skipped
- WorkDay records are created automatically
- External tokens are not stored - used only for the sync request

## Tests

```bash
# Run all backend tests
docker compose exec backend python -m pytest

# Run tests with coverage
docker compose exec backend python -m pytest --cov=apps

# Run tests for a specific module
docker compose exec backend python -m pytest apps/workdays/

# Run frontend tests
docker compose exec frontend npm test
```

## Development

```bash
# Create migrations
docker compose exec backend python manage.py makemigrations

# Apply migrations
docker compose exec backend python manage.py migrate

# Create superuser
docker compose exec backend python manage.py createsuperuser

# Django shell
docker compose exec backend python manage.py shell
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Debug mode | `False` |
| `SECRET_KEY` | Django secret key | Dev default when DEBUG=True, **required in production** |
| `DATABASE_URL` | PostgreSQL connection URL | `sqlite:///db.sqlite3` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `EXTERNAL_TIME_MANAGER_URL` | External time manager URL | - |

### Production Security

In production (`DEBUG=False`), `SECRET_KEY` **must** be set as an environment variable. The application will fail to start without it.

```bash
# Generate a secure secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## License

MIT
