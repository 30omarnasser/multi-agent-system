.PHONY: up down build reset logs test health

# Start all services
up:
	docker compose up -d
	@echo "✅ System running at http://localhost:8000"

# Stop all services
down:
	docker compose down

# Rebuild from scratch
build:
	docker compose build --no-cache

# Full reset — deletes all data
reset:
	docker compose down -v
	@echo "✅ Reset complete"

# View API logs
logs:
	docker compose logs api -f

# Run full regression tests
test:
	python tests/test_week3.py
	python tests/test_week4.py

# Check system health
health:
	@curl -s http://localhost:8000/health | python -m json.tool

# Start in production mode
prod:
	docker compose -f docker-compose.prod.yml up -d

# Stop production
prod-down:
	docker compose -f docker-compose.prod.yml down