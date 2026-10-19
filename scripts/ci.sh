#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_VERSION="3.12"
PROJECT_DIR="."
REQUIREMENTS="requirements.txt"
TEST_CMD=""
FRONTEND_DIR=""
export SECRET_KEY="${SECRET_KEY:-ci-only-insecure-key-not-a-secret}"
export DEBUG="${DEBUG:-False}"

part="${1:-all}"
step() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

python_env() {
    local venv="${CI_GATE_VENV:-$PWD/.venv-ci}"
    if [ ! -x "$venv/bin/python" ]; then
        step "creating virtualenv ($venv, Python $PYTHON_VERSION)"
        if command -v uv >/dev/null 2>&1; then
            uv venv --quiet --python "$PYTHON_VERSION" "$venv"
        else
            "python$PYTHON_VERSION" -m venv "$venv"
        fi
    fi
    export VIRTUAL_ENV="$venv" PATH="$venv/bin:$PATH"

    local lock="$PROJECT_DIR/uv.lock" hash stamp="$venv/.ci-deps"
    if [ -f "$lock" ]; then
        hash=$(cat "$PROJECT_DIR/pyproject.toml" "$lock" | sha256sum | cut -c1-16)
    else
        hash=$( (cd "$PROJECT_DIR" && cat $REQUIREMENTS) | sha256sum | cut -c1-16)
    fi
    [ "$(cat "$stamp" 2>/dev/null)" = "$hash" ] && return 0

    step "installing Python dependencies"
    if [ -f "$lock" ]; then
        (cd "$PROJECT_DIR" && UV_PROJECT_ENVIRONMENT="$venv" uv sync --quiet --frozen)
    else
        local args=() r
        for r in $REQUIREMENTS; do args+=(-r "$r"); done
        if command -v uv >/dev/null 2>&1; then
            (cd "$PROJECT_DIR" && uv pip install --quiet "${args[@]}")
        else
            (cd "$PROJECT_DIR" && python -m pip install --quiet "${args[@]}")
        fi
    fi
    echo "$hash" > "$stamp"
}

require_tests_ran() {
    if ! grep -Eq '(^Ran [1-9][0-9]* tests?)|([1-9][0-9]* passed)' "$1"; then
        echo "ERROR: no tests ran. Add real tests before pushing." >&2
        return 1
    fi
}

backend() {
    python_env
    local log
    log=$(mktemp)
    trap 'rm -f "$log"' RETURN
    (
        cd "$PROJECT_DIR"
        if [ -f manage.py ]; then
            step "Django system check"
            python manage.py check
            step "migrations match the models"
            python manage.py makemigrations --check --dry-run
        fi
        step "tests"
        if [ -n "$TEST_CMD" ]; then
            eval "$TEST_CMD"
        elif [ -f manage.py ]; then
            python manage.py test
        else
            python -m pytest
        fi
    ) 2>&1 | tee "$log"
    require_tests_ran "$log"
}

frontend() {
    [ -n "$FRONTEND_DIR" ] || return 0
    (
        cd "$FRONTEND_DIR"
        step "frontend: npm ci"
        npm ci --no-audit --no-fund
        if npm run | grep -q '^  lint$'; then
            step "frontend: lint"
            npm run lint
        fi
        if npm run | grep -q '^  test$'; then
            step "frontend: test"
            npm test
        fi
        step "frontend: build"
        npm run build
    )
}

case "$part" in
    all) backend; frontend ;;
    backend) backend ;;
    frontend) frontend ;;
    *) echo "usage: scripts/ci.sh [all|backend|frontend]" >&2; exit 2 ;;
esac
step "all checks passed"
