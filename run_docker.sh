#!/usr/bin/env bash
set -euo pipefail

# Docker management script for VinoBuzz

compose_cmd() {
    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

function show_help() {
    echo "Usage: ./run_docker.sh [command]"
    echo ""
    echo "Services (after docker-compose up):"
    echo "  Frontend: http://localhost:3042"
    echo "  Backend API: http://localhost:8042"
    echo ""
    echo "Commands:"
    echo "  build       Build all Docker images"
    echo "  up          Start services with docker-compose"
    echo "  down        Stop and remove containers"
    echo "  logs        Show logs from all services"
    echo "  shell       Open shell in backend container"
    echo "  test        Run backend tests in container"
    echo "  playwright-check  Run Playwright browser self-check in container"
    echo "  clean       Remove containers, volumes, and images"
    echo "  push        Build and push to registry (requires REGISTRY env var)"
    echo ""
    echo "Examples:"
    echo "  ./run_docker.sh build"
    echo "  ./run_docker.sh up -d    # detached mode"
    echo "  ./run_docker.sh logs -f  # follow logs"
}

function build_images() {
    echo "==> Building Docker images..."
    compose_cmd build --no-cache "$@"
}

function start_services() {
    echo "==> Starting VinoBuzz services..."
    compose_cmd up "$@"
}

function stop_services() {
    echo "==> Stopping VinoBuzz services..."
    compose_cmd down "$@"
}

function show_logs() {
    compose_cmd logs "$@"
}

function open_shell() {
    compose_cmd exec backend bash
}

function run_tests() {
    echo "==> Running backend tests..."
    compose_cmd exec backend bash -c "cd /app && python -m pytest backend/tests/ -v"
}

function run_playwright_check() {
    echo "==> Running Playwright self-check..."
    compose_cmd exec playwright curl -s http://localhost:8000/self-check | python3 -m json.tool
}

function clean_all() {
    echo "==> Cleaning up Docker resources..."
    compose_cmd down -v --rmi all --remove-orphans
    docker system prune -f
}

function push_images() {
    local registry=${REGISTRY:-"docker.io/yourusername"}
    echo "==> Pushing images to $registry..."
    
    docker tag vinobuzz-backend:latest $registry/vinobuzz-backend:latest
    docker tag vinobuzz-frontend:latest $registry/vinobuzz-frontend:latest
    
    docker push $registry/vinobuzz-backend:latest
    docker push $registry/vinobuzz-frontend:latest
}

# Main command handling
case "${1:-help}" in
    build)
        shift
        build_images "$@"
        ;;
    up|start)
        shift
        start_services "$@"
        ;;
    down|stop)
        shift
        stop_services "$@"
        ;;
    logs)
        shift
        show_logs "$@"
        ;;
    shell|bash)
        open_shell
        ;;
    test)
        run_tests
        ;;
    playwright-check)
        run_playwright_check
        ;;
    clean|reset)
        clean_all
        ;;
    push)
        push_images
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
