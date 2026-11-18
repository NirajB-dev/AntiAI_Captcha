#Author: Pravigya


"""Proof-of-Work Layer - Server Verification"""
import hashlib
import secrets

class ProofOfWorkVerifier:
    def __init__(self):
        self.challenges = {}  # session_id -> challenge
    
    def generate_challenge(self, session_id):
        """Generate random challenge for client"""
        challenge = secrets.token_hex(16)
        self.challenges[session_id] = challenge
        return challenge
    
    def verify(self, session_id, nonce, claimed_hash, difficulty=4):
        """Verify PoW solution"""
        if session_id not in self.challenges:
            return False, "No challenge found"
        
        challenge = self.challenges[session_id]
        target = '0' * difficulty
        
        # Recompute hash
        message = f"{challenge}{nonce}".encode()
        actual_hash = hashlib.sha256(message).hexdigest()
        
        # Verify
        valid = actual_hash.startswith(target) and actual_hash == claimed_hash
        
        # Clean up
        if valid:
            del self.challenges[session_id]
        
        return valid, "Valid PoW" if valid else "Invalid PoW"
    
    def get_difficulty(self, risk_score):
        """Adjust difficulty based on suspicion level"""
        if risk_score > 0.7:
            return 3  # High suspicion
        elif risk_score > 0.4:
            return 3  # Medium suspicion
        return 2  # Normal