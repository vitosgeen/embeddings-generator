#!/bin/bash
# Simple deployment script for embeddings service
# Usage: ./deploy.sh [production|staging|local]

set -e

ENVIRONMENT=${1:-local}
SERVICE_NAME="embeddings-generator"
INSTALL_DIR="/opt/${SERVICE_NAME}"
SERVICE_USER="embeddings"

echo "🚀 Deploying ${SERVICE_NAME} to ${ENVIRONMENT} environment..."

# Function to create virtual environment and install dependencies
setup_python_env() {
    echo "🐍 Setting up Python environment..."
    
    if [ "$ENVIRONMENT" = "local" ]; then
        VENV_PATH=".venv"
    else
        VENV_PATH="${INSTALL_DIR}/.venv"
    fi
    
    python3 -m venv "$VENV_PATH"
    source "$VENV_PATH/bin/activate"
    
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ Python environment ready at $VENV_PATH"
}

# Function to copy application files
deploy_application() {
    echo "📦 Deploying application files..."
    
    if [ "$ENVIRONMENT" != "local" ]; then
        # Production deployment
        sudo mkdir -p "$INSTALL_DIR"
        sudo cp -r app proto main.py requirements.txt "$INSTALL_DIR/"
        sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
        echo "✅ Files deployed to $INSTALL_DIR"
    else
        echo "✅ Local deployment - files already in place"
    fi
}

# Function to create systemd service (production only)
setup_service() {
    if [ "$ENVIRONMENT" = "production" ]; then
        echo "🔧 Setting up systemd service..."
        
        sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Embeddings Generator Service
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/.venv/bin
ExecStart=$INSTALL_DIR/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable ${SERVICE_NAME}
        echo "✅ Systemd service configured"
    fi
}

# Function to start the service
start_service() {
    echo "🎯 Starting ${SERVICE_NAME}..."
    
    if [ "$ENVIRONMENT" = "local" ]; then
        echo "🌐 Starting locally on http://localhost:8000"
        source .venv/bin/activate
        python main.py
    else
        sudo systemctl start ${SERVICE_NAME}
        sudo systemctl status ${SERVICE_NAME}
        echo "✅ Service started and enabled"
    fi
}

# Main deployment flow
main() {
    case $ENVIRONMENT in
        production|staging)
            # Create service user if it doesn't exist
            if ! id "$SERVICE_USER" &>/dev/null; then
                sudo useradd -r -s /bin/false "$SERVICE_USER"
            fi
            
            deploy_application
            setup_python_env
            setup_service
            start_service
            ;;
        local)
            setup_python_env
            start_service
            ;;
        *)
            echo "❌ Invalid environment: $ENVIRONMENT"
            echo "Usage: $0 [production|staging|local]"
            exit 1
            ;;
    esac
}

# Health check function
health_check() {
    echo "🔍 Performing health check..."
    sleep 5
    
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Service is healthy!"
    else
        echo "⚠️ Health check failed - service may still be starting"
    fi
}

# Run deployment
main "$@"

# Optional health check
if [ "$ENVIRONMENT" != "local" ]; then
    health_check
fi

echo "🎉 Deployment complete!"
echo "📡 Service endpoints:"
echo "  - REST API: http://localhost:8000"
echo "  - gRPC: localhost:50051"
echo "  - Health: http://localhost:8000/health"