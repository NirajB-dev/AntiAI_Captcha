#Author: Niraj


"""
CAPTCHA Security Configuration
Adjust these settings based on your security requirements
"""

class SecurityLevel:
    """Predefined security levels"""
    
    # 🟢 LOW - Easy for users, less secure (testing/low-risk applications)
    LOW = {
        'ml_threshold': 0.25,
        'advanced_threshold': 0.60,
        'combined_threshold': 0.55,
        'min_events': 15,
        'min_targets': 3,
        'max_attempts': 10,
        'attempt_cooldown': 5,  # seconds
        'fingerprint_risk_max': 0.8,
        'pow_difficulty_base': 3,
        'session_timeout': 7200,  # 2 hours
        'name': 'LOW_SECURITY'
    }
    
    # 🟡 MEDIUM - Balanced security (recommended for most applications)
    MEDIUM = {
        'ml_threshold': 0.55,
        'advanced_threshold': 0.60,
        'combined_threshold': 0.58,
        'min_events': 15,
        'min_targets': 4,
        'max_attempts': 5,
        'attempt_cooldown': 10,  # seconds
        'fingerprint_risk_max': 0.65,
        'pow_difficulty_base': 4,
        'session_timeout': 3600,  # 1 hour
        'name': 'MEDIUM_SECURITY'
    }
    
    # 🔴 HIGH - Strong security (financial/sensitive applications)
    HIGH = {
        'ml_threshold': 0.75,
        'advanced_threshold': 0.80,
        'combined_threshold': 0.78,
        'min_events': 25,
        'min_targets': 5,
        'max_attempts': 3,
        'attempt_cooldown': 30,  # seconds
        'fingerprint_risk_max': 0.4,
        'pow_difficulty_base': 5,
        'session_timeout': 1800,  # 30 minutes
        'name': 'HIGH_SECURITY'
    }
    
    # 🛡️ MAXIMUM - Very strict (critical systems only)
    MAXIMUM = {
        'ml_threshold': 0.85,
        'advanced_threshold': 0.85,
        'combined_threshold': 0.85,
        'min_events': 30,
        'min_targets': 5,
        'max_attempts': 2,
        'attempt_cooldown': 60,  # seconds
        'fingerprint_risk_max': 0.3,
        'pow_difficulty_base': 6,
        'session_timeout': 900,  # 15 minutes
        'name': 'MAXIMUM_SECURITY'
    }

# 🎯 CURRENT ACTIVE CONFIGURATION
# Change this to adjust your security level
ACTIVE_CONFIG = SecurityLevel.MEDIUM  # ⬅️ CHANGE THIS

# Individual overrides (optional)
CUSTOM_CONFIG = {
    # Uncomment and modify any setting you want to customize:
    # 'ml_threshold': 0.70,
    # 'max_attempts': 3,
    # 'session_timeout': 3600,
}

def get_config():
    """Get active security configuration with custom overrides"""
    config = ACTIVE_CONFIG.copy()
    config.update(CUSTOM_CONFIG)
    return config

# Human-readable descriptions
CONFIG_DESCRIPTIONS = {
    'ml_threshold': 'Machine Learning confidence score required (0-1)',
    'advanced_threshold': 'Advanced ML model confidence required (0-1)',
    'combined_threshold': 'Combined ML scores threshold (0-1)',
    'min_events': 'Minimum mouse/touch events required',
    'min_targets': 'Minimum targets that must be hit',
    'max_attempts': 'Maximum CAPTCHA attempts before lockout',
    'attempt_cooldown': 'Seconds to wait between failed attempts',
    'fingerprint_risk_max': 'Maximum browser fingerprint risk allowed (0-1)',
    'pow_difficulty_base': 'Proof-of-work difficulty level (1-10)',
    'session_timeout': 'Seconds before verification expires',
}
