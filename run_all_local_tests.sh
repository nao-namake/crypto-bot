#!/bin/bash
# Master test script to run all local tests

echo "=========================================="
echo "Starting Local Tests for CI/CD Pipeline"
echo "=========================================="

# Make scripts executable
chmod +x test_docker_local.sh
chmod +x test_terraform_local.sh

# Run Docker tests
echo "Starting Docker tests..."
./test_docker_local.sh
DOCKER_EXIT_CODE=$?

if [ $DOCKER_EXIT_CODE -eq 0 ]; then
    echo "✅ Docker tests passed!"
    
    # Run Terraform tests only if Docker tests passed
    echo "Starting Terraform tests..."
    ./test_terraform_local.sh
    TERRAFORM_EXIT_CODE=$?
    
    if [ $TERRAFORM_EXIT_CODE -eq 0 ]; then
        echo "✅ Terraform tests passed!"
        echo "=========================================="
        echo "🎉 All local tests completed successfully!"
        echo "Ready for CI/CD pipeline execution."
        echo "=========================================="
        exit 0
    else
        echo "❌ Terraform tests failed!"
        exit 1
    fi
else
    echo "❌ Docker tests failed!"
    exit 1
fi