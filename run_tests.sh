#!/bin/bash

# Script để chạy unit tests

echo "Running unit tests..."

# Chạy pytest trực tiếp (local - không dùng Docker)
pytest tests/ -v

# Hoặc nếu muốn chạy tests cho specific file:
# pytest tests/test_auth_register.py -v
# pytest tests/test_user_get_me.py -v
# pytest tests/test_user_delete_me.py -v

# Nếu muốn chạy trong Docker container, uncomment dòng dưới:
# docker-compose exec app pytest tests/ -v

echo "Tests completed!"
