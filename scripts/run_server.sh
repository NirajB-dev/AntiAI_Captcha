#Author: Rishi

#!/bin/bash

# Motor-Timing CAPTCHA Server Startup Script
# ==========================================

# Configuration
DEFAULT_PORT=5001
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Motor-Timing CAPTCHA Server${NC}"
echo -e "${BLUE}=======================================${NC}"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/requirements.txt" ]; then
    echo -e "${RED}❌ Error: Could not find project root directory${NC}"
    echo -e "${YELLOW}💡 Make sure you're running this script from the project directory${NC}"
    exit 1
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 is not installed or not in PATH${NC}"
    echo -e "${YELLOW}💡 Please install Python 3.7+ and try again${NC}"
    exit 1
fi

# Get port from command line argument or use default
PORT=${1:-$DEFAULT_PORT}

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo -e "${YELLOW}⚠️  Port $PORT is already in use${NC}"
    
    # Try to kill existing process
    echo -e "${BLUE}🔄 Attempting to stop existing server...${NC}"
    pkill -f "python.*server.py" 2>/dev/null
    sleep 2
    
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${RED}❌ Could not free port $PORT${NC}"
        echo -e "${YELLOW}💡 Try using a different port: $0 5002${NC}"
        exit 1
    else
        echo -e "${GREEN}✅ Previous server stopped successfully${NC}"
    fi
fi

# Check if model files exist
MODEL_DIR="$PROJECT_ROOT/models"
if [ ! -f "$MODEL_DIR/advanced_motor_captcha_model.pkl" ]; then
    echo -e "${YELLOW}⚠️  Advanced model not found. Training initial model...${NC}"
    cd "$PROJECT_ROOT/src/backend"
    python3 advanced_training.py
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Initial model training completed${NC}"
    else
        echo -e "${YELLOW}⚠️  Model training had issues, but continuing...${NC}"
    fi
fi

# Start the server
echo -e "${BLUE}🌐 Starting server on port $PORT...${NC}"
echo -e "${BLUE}───────────────────────────────────────${NC}"

cd "$PROJECT_ROOT/src/backend"
export FLASK_ENV=development
export FLASK_DEBUG=1

# Set OpenMP library path for XGBoost on macOS
export DYLD_LIBRARY_PATH="/opt/homebrew/opt/libomp/lib:$DYLD_LIBRARY_PATH"

# Display startup information
echo -e "${GREEN}✅ Server Configuration:${NC}"
echo -e "   📂 Project Root: $PROJECT_ROOT"
echo -e "   🐍 Python: $(python3 --version 2>&1)"
echo -e "   🌐 Port: $PORT"
echo -e ""
echo -e "${GREEN}🤖 ML Models:${NC}"
if [ -f "$MODEL_DIR/motor_captcha_model.pkl" ]; then
    echo -e "   ✅ RandomForest Model: motor_captcha_model.pkl"
else
    echo -e "   ❌ RandomForest Model: Not found"
fi
if [ -f "$MODEL_DIR/mouse_model_xgb_5.pkl" ]; then
    echo -e "   ✅ XGBoost Model: mouse_model_xgb_5.pkl (11 features)"
    echo -e "      └─ Thresholds: BOT < 0.20 | UNSURE 0.20-0.60 | HUMAN > 0.60"
else
    echo -e "   ❌ XGBoost Model: Not found"
fi
if [ -f "$MODEL_DIR/advanced_motor_captcha_model.pkl" ]; then
    echo -e "   ✅ Advanced Model: advanced_motor_captcha_model.pkl"
else
    echo -e "   ⚠️  Advanced Model: Not found (optional)"
fi
echo -e ""
echo -e "${GREEN}📱 Available Interfaces:${NC}"
echo -e "   🔗 Main CAPTCHA:        ${BLUE}http://localhost:$PORT/${NC}"
echo -e "   🧠 Training Interface:  ${BLUE}http://localhost:$PORT/training_interface.html${NC}"
echo -e "   🎯 Attack Visualizer:   ${BLUE}http://localhost:$PORT/attack_visualizer.html${NC}"
echo -e ""
echo -e "${YELLOW}💡 Press Ctrl+C to stop the server${NC}"
echo -e "${BLUE}───────────────────────────────────────${NC}"

# Start the server
python3 server.py $PORT

# Cleanup on exit
echo -e "\n${BLUE}🛑 Server stopped${NC}"
