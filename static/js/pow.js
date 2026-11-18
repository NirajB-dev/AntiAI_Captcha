//Author: Pravigya


// Proof-of-Work Layer - Minimal Implementation
class ProofOfWork {
    constructor(difficulty = 4) {
        this.difficulty = difficulty;
        this.solution = null;
        this.solving = false;
    }

    async sha256(message) {
        const msgBuffer = new TextEncoder().encode(message);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        return Array.from(new Uint8Array(hashBuffer))
            .map(b => b.toString(16).padStart(2, '0')).join('');
    }

    async solve(challenge, difficulty = this.difficulty) {
        this.solving = true;
        const target = '0'.repeat(difficulty);
        let nonce = 0;
        
        while (this.solving) {
            const hash = await this.sha256(challenge + nonce);
            if (hash.startsWith(target)) {
                this.solution = { nonce, hash };
                return this.solution;
            }
            nonce++;
            if (nonce % 100 === 0) await new Promise(r => setTimeout(r, 0)); // Don't block UI
        }
    }

    stop() {
        this.solving = false;
    }

    getProof() {
        return this.solution;
    }
}