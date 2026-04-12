#!/bin/bash
echo "⚠️  WARNING: This will delete all data (Postgres + Redis volumes)"
read -p "Are you sure? (y/N): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    echo "🗑️  Resetting system..."
    docker compose down -v
    echo "✅ Reset complete. Run ./scripts/start.sh to restart."
else
    echo "Cancelled."
fi