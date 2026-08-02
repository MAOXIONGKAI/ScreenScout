#!/usr/bin/env bash

# Exit on error
set -e

# ScreenScout Task Runner Helper Script

if [ $# -eq 0 ]; then
  make help
  exit 0
fi

case "$1" in
  setup|db-up|db-down|db-logs|db-psql|scrape-cinemas|scrape-movies|scrape-gv|scrape-shaw|clean-db|run-all|docker-scrape-cinemas|docker-scrape-movies|docker-scrape-gv|docker-scrape-shaw|docker-clean-db|docker-run-all|help)
    make "$1"
    ;;
  *)
    echo -e "\033[31mUnknown command: $1\033[0m"
    echo -e "Run \033[36m./run.sh help\033[0m or \033[36mmake help\033[0m for available commands."
    exit 1
    ;;
esac
