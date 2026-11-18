//Author: Rishi

class AttackVisualizer {
    constructor() {
        this.canvas = document.getElementById('attackCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.logEl = document.getElementById('attackLog');
        this.statusEl = document.getElementById('attackStatus');
        this.powStatusEl = document.getElementById('powStatus');
        this.verdictEl = document.getElementById('verdictBadge');
        this.scoreLineEl = document.getElementById('scoreLine');
        this.securityLevelEl = document.getElementById('securityLevel');

        this.strategyEl = document.getElementById('strategy');
        this.targetsEl = document.getElementById('targets');
        this.stepsEl = document.getElementById('steps');
        this.jitterEl = document.getElementById('jitter');
        this.delayEl = document.getElementById('baseDelay');
        this.useAdvancedEl = document.getElementById('useAdvanced');

        this.runBtn = document.getElementById('runAttack');

        this.pow = new ProofOfWork();
        this.fp = new BrowserFingerprint();

        this.events = [];
        this.targets = [];
        this.animFrame = null;

        this.bindUI();
        this.fetchSecurityLevel();
    }

    bindUI() {
        this.runBtn.addEventListener('click', () => this.runAttack());
    }

    async fetchSecurityLevel() {
        try {
            const res = await fetch('/security/config');
            const data = await res.json();
            const level = data?.current_config?.name || 'CUSTOM';
            this.securityLevelEl.textContent = `Security: ${level}`;
        } catch (e) {
            this.securityLevelEl.textContent = 'Security: unknown';
        }
    }

    log(message) {
        const ts = new Date().toLocaleTimeString();
        this.logEl.textContent = `[${ts}] ${message}\n${this.logEl.textContent}`;
    }

    setStatus(msg) {
        this.statusEl.textContent = msg;
    }

    setPowStatus(msg) {
        this.powStatusEl.textContent = msg;
    }

    setVerdict(pass, scoreText) {
        this.verdictEl.textContent = pass ? 'PASS' : 'FAIL';
        this.verdictEl.className = `badge ${pass ? 'pass' : 'fail'}`;
        this.scoreLineEl.textContent = scoreText;
    }

    resetCanvas() {
        cancelAnimationFrame(this.animFrame);
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    generateTargets(count) {
        const targets = [];
        const margin = 40;
        for (let i = 0; i < count; i++) {
            targets.push({
                id: i + 1,
                x: margin + Math.random() * (this.canvas.width - margin * 2),
                y: margin + Math.random() * (this.canvas.height - margin * 2),
            });
        }
        return targets;
    }

    easeInOut(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    generateEvents(strategy, targets, stepsPerLeg, jitterPx, baseDelayMs) {
        const events = [];
        const baseTime = performance.now();
        let t = baseTime;

        // Start near canvas center
        let current = {
            x: this.canvas.width / 2 + (Math.random() * 80 - 40),
            y: this.canvas.height / 2 + (Math.random() * 80 - 40),
        };
        events.push({ ...current, t, type: 'start' });

        for (const target of targets) {
            const ctrl = {
                x: (current.x + target.x) / 2 + (Math.random() * 80 - 40),
                y: (current.y + target.y) / 2 + (Math.random() * 80 - 40),
            };

            for (let step = 1; step <= stepsPerLeg; step++) {
                const rawProgress = step / stepsPerLeg;
                const eased = strategy === 'noisy' ? this.easeInOut(rawProgress) : rawProgress;

                let x, y;
                if (strategy === 'curve') {
                    // Quadratic Bezier
                    const inv = 1 - eased;
                    x = inv * inv * current.x + 2 * inv * eased * ctrl.x + eased * eased * target.x;
                    y = inv * inv * current.y + 2 * inv * eased * ctrl.y + eased * eased * target.y;
                } else {
                    // Linear / noisy-linear
                    x = current.x + (target.x - current.x) * eased;
                    y = current.y + (target.y - current.y) * eased;
                }

                // Add jitter
                const noise = jitterPx / 2;
                x += (Math.random() - 0.5) * noise * 2;
                y += (Math.random() - 0.5) * noise * 2;

                t += baseDelayMs + Math.random() * 6;
                events.push({ x, y, t, type: 'move' });
            }

            // Simulate a small pause before confirming the hit
            t += Math.random() * 30;
            events.push({ x: target.x, y: target.y, t, type: 'hit', targetId: target.id });
            current = { x: target.x, y: target.y };
        }

        return events;
    }

    renderTargets() {
        this.ctx.save();
        for (const target of this.targets) {
            this.ctx.beginPath();
            this.ctx.fillStyle = 'rgba(59,130,246,0.3)';
            this.ctx.strokeStyle = 'rgba(59,130,246,0.4)';
            this.ctx.lineWidth = 2;
            this.ctx.arc(target.x, target.y, 12, 0, Math.PI * 2);
            this.ctx.fill();
            this.ctx.stroke();

            this.ctx.fillStyle = '#cbd5e1';
            this.ctx.font = '12px monospace';
            this.ctx.fillText(target.id, target.x - 4, target.y + 4);
        }
        this.ctx.restore();
    }

    playback(events) {
        if (!events.length) return;
        this.resetCanvas();
        this.renderTargets();

        const start = performance.now();
        const base = events[0].t;
        let idx = 0;
        let lastPoint = events[0];

        const drawFrame = () => {
            const elapsed = performance.now() - start;
            while (idx < events.length && (events[idx].t - base) <= elapsed) {
                const ev = events[idx];
                this.ctx.strokeStyle = ev.type === 'hit' ? '#22c55e' : '#60a5fa';
                this.ctx.lineWidth = ev.type === 'hit' ? 3 : 2;
                this.ctx.beginPath();
                this.ctx.moveTo(lastPoint.x, lastPoint.y);
                this.ctx.lineTo(ev.x, ev.y);
                this.ctx.stroke();

                this.ctx.fillStyle = ev.type === 'hit' ? '#22c55e' : '#93c5fd';
                this.ctx.beginPath();
                this.ctx.arc(ev.x, ev.y, ev.type === 'hit' ? 6 : 3, 0, Math.PI * 2);
                this.ctx.fill();

                lastPoint = ev;
                idx++;
            }

            if (idx < events.length) {
                this.animFrame = requestAnimationFrame(drawFrame);
            }
        };

        drawFrame();
    }

    async solvePow(challenge, difficulty) {
        this.setPowStatus(`PoW: solving (diff ${difficulty})`);
        const start = performance.now();
        const proof = await this.pow.solve(challenge, difficulty);
        const ms = Math.round(performance.now() - start);
        this.setPowStatus(`PoW: solved in ${ms}ms`);
        return proof;
    }

    async runAttack() {
        this.setVerdict(false, 'Score: -');
        this.log('Starting attack run...');

        const strategy = this.strategyEl.value;
        const targetCount = parseInt(this.targetsEl.value, 10) || 6;
        const steps = parseInt(this.stepsEl.value, 10) || 22;
        const jitter = parseInt(this.jitterEl.value, 10) || 0;
        const baseDelay = parseInt(this.delayEl.value, 10) || 10;
        const useAdvanced = this.useAdvancedEl.checked;

        try {
            this.setStatus('Requesting challenge...');
            const challengeRes = await fetch('/get-challenge');
            const challengeData = await challengeRes.json();
            const sessionId = challengeData.session_id;
            const challenge = challengeData.challenge;
            this.log(`Challenge received (session ${sessionId.slice(0, 6)}...)`);

            this.setStatus('Collecting fingerprint...');
            const fingerprint = await this.fp.collect();
            this.log('Fingerprint collected');

            // Slightly higher difficulty to satisfy lower targets too
            const powProof = await this.solvePow(challenge, 3);

            this.targets = this.generateTargets(targetCount);
            const events = this.generateEvents(strategy, this.targets, steps, jitter, baseDelay);
            this.events = events;
            this.playback(events);
            this.setStatus('Dispatching payload to /verify-motor-captcha...');

            const payload = {
                events,
                targetSequence: this.targets.map(t => t.id),
                targetsHit: this.targets.length,
                canvasWidth: this.canvas.width,
                canvasHeight: this.canvas.height,
                fingerprint,
                session_id: sessionId,
                pow_nonce: powProof?.nonce || 0,
                pow_hash: powProof?.hash || '',
                use_advanced: useAdvanced
            };

            const res = await fetch('/verify-motor-captcha', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            const score = data.combined_confidence || data.advanced_score || data.confidence || 0;
            const scoreText = `Score: ${score ? score.toFixed(3) : 'n/a'} | Reason: ${data.reason || 'n/a'}`;
            this.setVerdict(!!data.verified, scoreText);
            this.log(`Server response: ${JSON.stringify(data, null, 2)}`);
            this.setStatus('Attack completed');
        } catch (err) {
            this.setStatus('Attack failed');
            this.setPowStatus('PoW: error');
            this.log(`Error: ${err.message}`);
            this.setVerdict(false, 'Score: -');
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new AttackVisualizer();
});
