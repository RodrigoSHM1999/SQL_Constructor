# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Django-based SQL Query Manager that allows users to create, execute, and export dynamic SQL queries against SQL Server databases. The system provides a secure framework for building parameterized queries with user-friendly forms and result visualization.

## Development Commands

### Setup and Installation
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

### Running the Application
```bash
# Development server
python manage.py runserver

# Run with specific settings
python manage.py runserver --settings=config.settings
```

### Testing
```bash
# Run all tests
pytest

# Run specific app tests
pytest apps/queries/

# Run with coverage
pytest --cov=apps/
```

### Database Operations
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Show current migration status
python manage.py showmigrations
```

## Architecture Overview

### Core Components

**Apps Structure:**
- `apps/core/`: Base application with common functionality
- `apps/queries/`: Main business logic for SQL query management

**Query Management System:**
- `DynamicQuery` model: Stores query templates with parameterized WHERE clauses
- `QueryParameter` model: Defines user-configurable parameters for queries  
- `QueryExecution` model: Logs all query executions for audit purposes

**Service Layer:**
- `QueryExecutorService`: Handles secure query execution with timeout and pagination
- `QueryBuilderService`: Constructs final SQL from templates and parameters
- `QueryValidatorService`: Validates queries for security (prevents dangerous SQL commands)

**Repository Pattern:**
- `SQLServerRepository`: Handles direct database interactions with pagination support using OFFSET/FETCH

### Security Features

**SQL Injection Protection:**
- Parameterized queries using numbered placeholders (%1, %2, etc.)
- Whitelist validation preventing dangerous SQL commands (DROP, DELETE, INSERT, UPDATE, ALTER, TRUNCATE, EXEC)
- Query timeout enforcement (configurable via SQL_QUERY_TIMEOUT)
- Result limit enforcement (MAX_RESULTS_LIMIT)

### Configuration

**Environment Variables:**
Required variables should be defined in `.env` (see `.env.example`):
- Database connection: `DB_NAME`, `DB_HOST`, `DB_DRIVER`
- Security: `SECRET_KEY`, `SQL_QUERY_TIMEOUT`, `MAX_RESULTS_LIMIT`
- Pagination: `RESULTS_PER_PAGE`

**Database:**
- Uses SQL Server with Windows Authentication
- Configured via `mssql-django` adapter with `pyodbc`
- Connection settings in `config/settings.py:DATABASES`

### Key Patterns

**Model Structure:**
- Models use Spanish field names (matches client requirements)
- Extensive use of `help_text` for admin interface guidance
- Custom validation in model `clean()` methods
- Proper indexing for performance

**Service Layer Pattern:**
- Business logic isolated in services directory
- Services handle cross-cutting concerns (logging, validation, security)
- Repository pattern separates database operations

**Template Organization:**
- Base template with Tailwind CSS styling
- Partials for reusable components (alerts, pagination, navbar)
- Crispy forms integration for form rendering

### Export Functionality

The system supports exporting query results to:
- Excel (.xlsx) via `openpyxl`
- CSV with UTF-8-BOM encoding for proper Excel import
- Files saved to `media/exports/` with timestamp naming

### Error Handling

- Comprehensive logging throughout the application
- User-friendly error messages in Spanish
- Query execution errors captured in `QueryExecution` logs
- Timeout handling for long-running queries

## Notes for Development

- The system is designed for read-only SQL operations only
- All dynamic queries must be approved and created by technical users
- End users only provide parameter values, not SQL code
- Pagination is handled automatically for large result sets
- The admin interface is the primary way to manage query templates