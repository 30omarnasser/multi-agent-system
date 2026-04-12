#!/bin/bash
set -e

echo "🤖 Starting Multi-Agent System..."
echo "=================================="

# Check Ollama is running
echo "Checking Ollama..."
if curl -s http://localhost:11434 > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "⚠️  Ollama not detected — start it with: ollama serve"
fi

# Check required models
echo "Checking models..."
if ollama list 2>/dev/null | grep -q "llama3"; then
    echo "✅ LLM model found"
else
    echo "📥 Pulling llama3.1:8b..."
    ollama pull llama3.1:8b
fi

if ollama list 2>/dev/null | grep -q "nomic-embed-text"; then
    echo "✅ Embedding model found"
else
    echo "📥 Pulling nomic-embed-text..."
    ollama pull nomic-embed-text
fi

# Start Docker services
echo ""
echo "Starting Docker services..."
docker compose up -d

echo ""
echo "✅ System started!"
echo "   API:      http://localhost:8000"
echo "   Swagger:  http://localhost:8000/docs"
echo "   UI:       http://localhost:8501"
echo "   MLflow:   http://localhost:5000"