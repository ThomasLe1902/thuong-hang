#!/bin/bash

# AI FTES Backend Docker Build Script
# Builds the backend application with proper tagging

set -e

echo "🚀 Building AI FTES Backend Docker Image..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build the Docker image
echo "🔨 Building hotonbao/ai-ftes-be:latest..."
docker build -t hotonbao/ai-ftes-be:latest .

# Verify the build
if docker images | grep -q "hotonbao/ai-ftes-be"; then
    echo "✅ Backend image built successfully!"
    echo "📦 Image: hotonbao/ai-ftes-be:latest"
    
    # Show image details
    echo ""
    echo "📊 Image Details:"
    docker images hotonbao/ai-ftes-be:latest
else
    echo "❌ Failed to build backend image"
    exit 1
fi

echo ""
echo "🎉 Build completed successfully!"
echo "💡 Next step: Run './start_full_stack.sh' to start the complete application with monitoring" 