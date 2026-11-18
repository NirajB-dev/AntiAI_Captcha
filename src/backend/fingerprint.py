#Author: Pravigya


"""Browser Fingerprinting Layer - Server Analysis"""
import hashlib
import json

class FingerprintAnalyzer:
    def __init__(self):
        self.known_fps = {}  # fp_hash -> count
    
    def analyze(self, fp):
        """Analyze fingerprint for bot indicators"""
        risk_score = 0.0
        flags = []
        
        # Automation tool detection
        if fp.get('webdriver'):
            risk_score += 0.4
            flags.append('webdriver_detected')
        if fp.get('phantom'):
            risk_score += 0.3
            flags.append('phantomjs_detected')
        if fp.get('selenium'):
            risk_score += 0.3
            flags.append('selenium_detected')
        if fp.get('headless'):
            risk_score += 0.35
            flags.append('headless_browser')
        
        # Impossible/suspicious values
        if fp.get('cores', 0) == 0:
            risk_score += 0.15
            flags.append('no_cpu_cores')
        if fp.get('plugins', -1) == 0:
            risk_score += 0.1
            flags.append('no_plugins')
        if fp.get('canvas') == 'error' or fp.get('webgl') == 'error':
            risk_score += 0.2
            flags.append('canvas_webgl_error')
        
        # Inconsistencies
        if 'Linux' in fp.get('platform', '') and 'Windows' in fp.get('ua', ''):
            risk_score += 0.25
            flags.append('platform_ua_mismatch')
        
        # Track frequency (same bot trying multiple times)
        fp_hash = self.hash_fp(fp)
        self.known_fps[fp_hash] = self.known_fps.get(fp_hash, 0) + 1
        if self.known_fps[fp_hash] > 5:
            risk_score += 0.3
            flags.append('repeated_fingerprint')
        
        return min(risk_score, 1.0), flags
    
    def hash_fp(self, fp):
        """Create hash of fingerprint"""
        fp_str = json.dumps(fp, sort_keys=True)
        return hashlib.sha256(fp_str.encode()).hexdigest()