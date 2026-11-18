# Anti-AI CAPTCHA System

**Group**: GROUP 5  
**Repository**: https://gitlab.scss.tcd.ie/bharambn/cs7ns1-mainproject2

A sophisticated Motor-Timing CAPTCHA system designed to distinguish humans from bots using advanced movement analysis, machine learning, and multi-layer security validation.

## ⚡ Quick Launch (Using Scripts)

### 🎯 One-Command Server Start
```bash
# Make script executable (first time only)
chmod +x scripts/run_server.sh

# Start full CAPTCHA server with all features
./scripts/run_server.sh

# Or with custom port
./scripts/run_server.sh 5002
```
**✅ Auto-configures**: Models, database, debug mode, and startup checks
**🌐 Available at**: http://localhost:5001

### � Quick Analytics Dashboard
```bash
# In a new terminal, start the dashboard
source .venv/bin/activate
python3 src/backend/dashboard.py
```
**📊 Dashboard at**: http://localhost:5002

### 🎮 Generate Test Data
```bash
# Populate with realistic sample data
python3 scripts/generate_mock_data.py
```

---

## 🚀 Manual Setup (Detailed)

### Prerequisites
- Python 3.8+ 
- Google Chrome browser (for testing attacks)
- 4GB+ RAM (for ML models)

### 1. Setup Environment
```bash
# Clone and enter directory
cd Captcha_Test

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies  
pip install -r requirements.txt
```

### 2. Start the CAPTCHA Server
```bash
# Start main CAPTCHA server on port 5001
python3 src/backend/server.py 5001
```

**✅ CAPTCHA Interface**: http://localhost:5001

### 3. Start Analytics Dashboard (Optional)
```bash
# In a new terminal (keep server running)
source .venv/bin/activate
python3 src/backend/dashboard.py
```

**📊 Analytics Dashboard**: http://localhost:5002

### 4. Test the System
Open http://localhost:5001 in your browser:
1. Fill in the fake transfer form
2. Click "Initiate Transfer" 
3. Complete the motor CAPTCHA by tapping numbered targets in sequence
4. Observe your success/failure and check analytics

## 🎯 System Architecture

### Core Components
- **Frontend**: HTML5 Canvas CAPTCHA with motor-timing analysis
- **Backend**: Flask server with 6-layer security pipeline
- **ML Models**: RandomForest + XGBoost for bot detection
- **Database**: SQLite analytics with comprehensive logging
- **Dashboard**: Real-time monitoring and attack analysis

### Security Layers
1. **Session Tracking**: Attempt limiting per browser fingerprint
2. **Fingerprint Analysis**: Automation detection (Selenium, headless browsers)
3. **Proof-of-Work**: SHA256 computational challenge (anti-spam)
4. **Motor Analysis**: 10-feature movement pattern classification
5. **XGBoost Detection**: Advanced bot pattern recognition
6. **Rules Engine**: Hard blocks for impossible human behavior

## 🛡️ Security Levels

Configure in `src/backend/security_config.py`:

| Level | ML Threshold | Max Attempts | PoW Difficulty | Use Case |
|-------|-------------|--------------|----------------|-----------|
| **LOW** | 0.25 | 10 | 3 | Development/Testing |
| **MEDIUM** | 0.55 | 5 | 4 | **Default** Production |
| **HIGH** | 0.75 | 3 | 5 | High Security |
| **MAXIMUM** | 0.85 | 2 | 6 | Maximum Protection |

```python
# Change security level
ACTIVE_CONFIG = SecurityLevel.HIGH  # MEDIUM is default
```

## 🤖 Testing Attacks

### Run Demo Attack Suite
```bash
# Test 3 different attack patterns
python3 demo_3_attacks.py
```

### Advanced LLM Vision Attack
```bash
# Set up Gemini API key
export GEMINI_API_KEY="your_api_key_here"
python3 llm_gemini.py
```

### Claude Vision Attack (Black-box)
```bash
# Set up Anthropic API key  
export ANTHROPIC_API_KEY="your_api_key_here"
python3 src/attackers/claude_attacker.py
```

### All Attack Patterns
```bash
cd src/attackers
python3 run_all_attackers.py http://localhost:5001
```

## 📊 Analytics & Monitoring

### Database Schema
- **captcha_attempts**: Main attempt log with success/failure
- **motor_events**: Detailed mouse movement data  
- **ml_detection**: ML model predictions and confidence scores
- **attack_logs**: Attack attempt details and detection methods

### Dashboard Features
- Real-time success rate charts
- Attack pattern analysis
- ML detection insights  
- Hourly activity distribution
- Recent attempts log

### Generate Sample Data
```bash
# Populate database with realistic test data
python3 scripts/generate_mock_data.py
```

## 🔧 Advanced Configuration

### Custom Security Settings
```python
# src/backend/security_config.py
CUSTOM_CONFIG = {
    'ml_threshold': 0.70,      # Human probability threshold
    'max_attempts': 3,         # Attempts per session  
    'fingerprint_risk_max': 0.5, # Max automation risk
    'pow_difficulty': 5,       # PoW leading zeros
    'min_targets': 4           # Targets to complete
}
```

### Model Training & Updates
```bash
# Retrain ML models with new data
python3 src/backend/advanced_training.py

# View training interface  
# Visit: http://localhost:5001/training_interface.html
```

### Load Balancing (Production)
```bash
# Start multiple server instances
python3 src/backend/server.py 5001 &
python3 src/backend/server.py 5002 &  
python3 src/backend/server.py 5003 &

# Start load balancer
python3 src/backend/load_balancer.py --port 8080 --backends "localhost:5001,localhost:5002,localhost:5003"
```

## 📁 Project Structure

```
Captcha_Test/
├── src/
│   ├── backend/          # Server components
│   │   ├── server.py     # Main Flask server
│   │   ├── security_config.py # Security levels
│   │   ├── dashboard.py  # Analytics dashboard
│   │   └── ...
│   ├── frontend/         # UI components  
│   ├── attackers/        # Attack simulation tools
│   └── solvers/          # Computer vision solvers
├── static/              # CSS, JS, assets
├── templates/           # HTML templates
├── models/             # ML model files (.pkl)
├── scripts/            # Utility scripts
├── captcha_analytics.db # SQLite database
└── requirements.txt    # Python dependencies
```

## 🔍 Troubleshooting

### Common Issues

**Server won't start**:
```bash
# Check if port is in use
lsof -i :5001
# Kill process if needed
kill -9 <PID>
```

**ML Model errors**:
```bash  
# Regenerate models
python3 src/backend/advanced_training.py
```

**Database issues**:
```bash
# Reset database (WARNING: deletes all data)
rm captcha_analytics.db
# Restart server to recreate
```

**Virtual environment issues**:
```bash
# Deactivate current environment
deactivate

# Remove and recreate
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Debug Mode
```bash
# Run server in debug mode for detailed logs
FLASK_DEBUG=1 python3 src/backend/server.py 5001
```



### System Behavior
- **Human Users**: Generous hit zones (50px), 8s per target, visual feedback
- **Bot Detection**: 10+ movement features analyzed by RandomForest + XGBoost
- **Attack Resistance**: Blocks linear movement, direct clicks, automation flags
- **Adaptive Security**: Escalates difficulty based on fingerprint risk

## ⚠️ Known Limitations

### Critical Security Gaps
1. **DOM Information Leak**: `motorCaptcha.targets` globally accessible
2. **Stealth Detection**: Advanced Selenium can bypass fingerprint analysis  
3. **Client-side PoW**: Computational challenge solved in browser

### Attack Success Rates
- **Basic Bots**: 0% success (blocked by rules layer)
- **Linear Movement**: ~5% success (blocked by ML)
- **Advanced Stealth**: ~15% success on MEDIUM (higher on HIGH/MAX)
- **LLM Vision**: ~45% success (expensive, detectable patterns)

## 🚦 Production Deployment

### Security Checklist
- [ ] Set security level to HIGH or MAXIMUM
- [ ] Configure proper session limits
- [ ] Monitor attack patterns via dashboard
- [ ] Regularly update ML models with new attack data
- [ ] Implement rate limiting at network level
- [ ] Use HTTPS for all connections

### Performance Optimization
- Pre-load ML models at startup
- Use Redis for session caching in production
- Implement database connection pooling
- Consider CDN for static assets

---

## 📄 License

This is a research/educational project demonstrating anti-AI CAPTCHA techniques.

## 🤝 Contributing

1. Test new attack patterns against the system
2. Analyze detection effectiveness via dashboard
3. Submit improvements to ML models or detection layers
4. Document new vulnerabilities or mitigations

---

**⚡ Ready to start? Run `python3 src/backend/server.py 5001` and visit http://localhost:5001**
