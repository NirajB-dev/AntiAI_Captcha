//Author: Niraj

// Motor-Timing & Trajectory CAPTCHA Implementation

class BrowserFingerprint {
    async collect() {
        const fp = {
            // Hardware/OS
            ua: navigator.userAgent,
            platform: navigator.platform,
            cores: navigator.hardwareConcurrency || 0,
            memory: navigator.deviceMemory || 0,
            screen: `${screen.width}x${screen.height}x${screen.colorDepth}`,
            
            // Browser features
            tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
            lang: navigator.language,
            plugins: navigator.plugins.length,
            
            // Canvas fingerprint
            canvas: this.getCanvasFP(),
            
            // WebGL fingerprint
            webgl: this.getWebGLFP(),
            
            // Audio fingerprint
            audio: await this.getAudioFP(),
            
            // Automation detection
            webdriver: navigator.webdriver || false,
            phantom: !!window._phantom || !!window.callPhantom,
            selenium: !!window.document.$cdc_ || !!window.document.$chrome_asyncScriptInfo,
            headless: await this.detectHeadless(),
            
            // Network timing
            rtt: navigator.connection?.rtt || 0,
            downlink: navigator.connection?.downlink || 0
        };
        
        return fp;
    }

    getCanvasFP() {
        try {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            ctx.textBaseline = 'top';
            ctx.font = '14px Arial';
            ctx.fillText('Browser FP', 2, 2);
            return canvas.toDataURL().slice(-50);
        } catch { return 'error'; }
    }

    getWebGLFP() {
        try {
            const canvas = document.createElement('canvas');
            const gl = canvas.getContext('webgl');
            const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
            return gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL).slice(0, 30);
        } catch { return 'error'; }
    }

    async getAudioFP() {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const analyser = ctx.createAnalyser();
            osc.connect(analyser);
            osc.disconnect();
            return analyser.frequencyBinCount.toString();
        } catch { return 'error'; }
    }

    async detectHeadless() {
        return !navigator.plugins.length || 
               navigator.webdriver ||
               !window.chrome ||
               /HeadlessChrome/.test(navigator.userAgent);
    }
}

class MotorTimingCaptcha {
    constructor() {
        this.canvas = document.getElementById('motorCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.events = []; // Array of {x, y, t, type} events
        this.targets = [];
        this.targetSequence = [];
        this.currentTargetIndex = 0;
        this.targetsHit = 0;
        this.startTime = null;
        this.animationFrame = null;
        this.timeRemaining = 30;
        this.timerInterval = null;
        this.isActive = false;
        this.targetLifetime = 8000; // 8 seconds per target (increased from 3)
        this.targetSpawnInterval = null;
        this.waitingForHit = false; // Only spawn next target after current is hit
        
        // Initialize layers
        this.pow = null;
        this.fingerprint = new BrowserFingerprint();
        this.sessionId = null;
        this.challenge = null;
        
        // Adjust canvas size for mobile
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
        
        this.initEventListeners();
    }



    resizeCanvas() {
        const maxWidth = Math.min(800, window.innerWidth - 40);
        const maxHeight = Math.min(500, window.innerHeight - 300);
        this.canvas.width = maxWidth;
        this.canvas.height = maxHeight;
    }

    initEventListeners() {
        document.getElementById('initiateBtn').addEventListener('click', () => this.showCaptcha());
        document.getElementById('cancelBtn').addEventListener('click', () => this.cancelCaptcha());
        document.getElementById('newTransferBtn').addEventListener('click', () => this.resetForm());
        
        // Mouse events
        this.canvas.addEventListener('mousedown', (e) => this.recordEvent(e, 'mousedown'));
        this.canvas.addEventListener('mousemove', (e) => this.recordEvent(e, 'mousemove'));
        this.canvas.addEventListener('mouseup', (e) => this.recordEvent(e, 'mouseup'));
        
        // Touch events
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.recordTouchEvent(touch, 'touchstart');
        });
        this.canvas.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            this.recordTouchEvent(touch, 'touchmove');
        });
        this.canvas.addEventListener('touchend', (e) => {
            e.preventDefault();
            if (e.changedTouches.length > 0) {
                const touch = e.changedTouches[0];
                this.recordTouchEvent(touch, 'touchend');
            }
        });
    }

    getCanvasCoordinates(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    recordEvent(e, type) {
        if (!this.isActive) return;
        
        const coords = this.getCanvasCoordinates(e);
        const timestamp = performance.now();
        
        this.events.push({
            x: coords.x,
            y: coords.y,
            t: timestamp,
            type: type
        });
        
        if (type === 'mousedown' || type === 'touchstart') {
            this.checkTargetHit(coords.x, coords.y);
        }
    }

    recordTouchEvent(touch, type) {
        if (!this.isActive) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const coords = {
            x: touch.clientX - rect.left,
            y: touch.clientY - rect.top
        };
        const timestamp = performance.now();
        
        this.events.push({
            x: coords.x,
            y: coords.y,
            t: timestamp,
            type: type
        });
        
        if (type === 'touchstart') {
            this.checkTargetHit(coords.x, coords.y);
        }
    }

    async showCaptcha() {
        const recipient = document.getElementById('recipient').value;
        const amount = document.getElementById('amount').value;

        if (!recipient || !amount || parseFloat(amount) <= 0) {
            alert('Please enter valid recipient and amount');
            return;
        }

        // Get PoW challenge from server
        try {
            const response = await fetch('/get-challenge');
            const data = await response.json();
            this.sessionId = data.session_id;
            this.challenge = data.challenge;
        } catch (error) {
            console.error('Failed to get challenge:', error);
            alert('Failed to initialize security check');
            return;
        }

        document.getElementById('transferSection').style.display = 'none';
        document.getElementById('captchaSection').style.display = 'block';
        
        this.startChallenge();
    }

    startChallenge() {
        // Reset state
        this.events = [];
        this.targets = [];
        this.currentTargetIndex = 0;
        this.targetsHit = 0;
        this.isActive = false;
        this.timeRemaining = 30;
        
        // Start PoW solving in background (adaptive difficulty will be set by server)
        this.pow = new ProofOfWork(2);
        this.pow.solve(this.challenge).catch(e => console.log('PoW interrupted:', e));
        
        // Generate random target sequence (3-5 targets)
        const numTargets = 3 + Math.floor(Math.random() * 3);
        this.targetSequence = Array.from({length: numTargets}, (_, i) => i + 1);
        
        document.getElementById('targetSequence').textContent = 
            `Tap targets in order: ${this.targetSequence.join(' → ')}`;
        document.getElementById('targetsHit').textContent = `Targets hit: 0 / ${numTargets}`;
        document.getElementById('progressBar').style.width = '0%';
        
        this.startTimer();
        
        // Start spawning targets after a short delay
        setTimeout(() => {
            this.isActive = true;
            this.startTime = performance.now();
            this.spawnNextTarget();
        }, 1000);
    }

    spawnNextTarget() {
        if (this.currentTargetIndex >= this.targetSequence.length) {
            // All targets spawned, wait for completion
            return;
        }

        const targetNumber = this.targetSequence[this.currentTargetIndex];
        const target = {
            id: targetNumber,
            x: 80 + Math.random() * (this.canvas.width - 160),
            y: 80 + Math.random() * (this.canvas.height - 160),
            radius: 35, // Increased from 20 to make easier to click
            hitRadius: 50, // Larger hit area for easier clicking
            spawnTime: performance.now(),
            lifetime: this.targetLifetime,
            color: this.getTargetColor(targetNumber),
            hit: false
        };

        this.targets.push(target);
        this.currentTargetIndex++;
        this.waitingForHit = true; // Wait for this target to be hit

        this.animate();
    }

    getTargetColor(number) {
        const colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
            '#F7DC6F', '#BB8FCE', '#85C1E2'
        ];
        return colors[(number - 1) % colors.length];
    }

    checkTargetHit(x, y) {
        for (let target of this.targets) {
            if (target.hit) continue;
            
            const distance = Math.sqrt(
                Math.pow(x - target.x, 2) + Math.pow(y - target.y, 2)
            );
            
            // Use larger hit radius for easier clicking
            if (distance <= target.hitRadius) {
                // Check if it's the correct target
                const expectedTarget = this.targetSequence[this.targetsHit];
                if (target.id === expectedTarget) {
                    target.hit = true;
                    this.targetsHit++;
                    this.waitingForHit = false; // Allow next target to spawn
                    
                    // Record hit event
                    this.events.push({
                        x: x,
                        y: y,
                        t: performance.now(),
                        type: 'hit',
                        targetId: target.id
                    });
                    
                    document.getElementById('targetsHit').textContent = 
                        `Targets hit: ${this.targetsHit} / ${this.targetSequence.length}`;
                    document.getElementById('progressBar').style.width = 
                        `${(this.targetsHit / this.targetSequence.length) * 100}%`;
                    document.getElementById('statusText').textContent = 
                        `✓ Target ${target.id} hit!`;
                    
                    // Spawn next target after a short delay
                    if (this.targetsHit < this.targetSequence.length) {
                        setTimeout(() => {
                            this.spawnNextTarget();
                        }, 500);
                    } else {
                        // All targets hit
                        setTimeout(() => this.verifyCaptcha(), 500);
                    }
                    
                    return true;
                } else {
                    // Wrong target - show message but don't block
                    document.getElementById('statusText').textContent = 
                        `Wrong target! Click target ${expectedTarget} first.`;
                    setTimeout(() => {
                        document.getElementById('statusText').textContent = 
                            `Tap target ${expectedTarget} in the correct order`;
                    }, 2000);
                }
            }
        }
        return false;
    }

    animate() {
        if (!this.isActive && this.targets.length === 0) return;
        
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        const currentTime = performance.now();
        
        // Draw and update targets
        for (let i = this.targets.length - 1; i >= 0; i--) {
            const target = this.targets[i];
            const age = currentTime - target.spawnTime;
            
            // Remove expired targets (only if not hit and waiting for next)
            if (age > target.lifetime && !target.hit) {
                this.targets.splice(i, 1);
                // If we were waiting for this target, spawn next one
                if (this.waitingForHit && this.currentTargetIndex < this.targetSequence.length) {
                    this.waitingForHit = false;
                    setTimeout(() => {
                        this.spawnNextTarget();
                    }, 500);
                }
                continue;
            }
            

            
            // Draw target
            this.ctx.save();
            
            if (target.hit) {
                this.ctx.globalAlpha = 0.5;
            } else {
                // Gentle pulsing effect (less distracting)
                const pulse = Math.sin(age / 300) * 0.15 + 1;
                this.ctx.scale(pulse, pulse);
            }
            
            // Draw hit area indicator (subtle outer ring)
            if (!target.hit) {
                this.ctx.strokeStyle = target.color;
                this.ctx.globalAlpha = 0.2;
                this.ctx.lineWidth = 2;
                this.ctx.beginPath();
                this.ctx.arc(target.x, target.y, target.hitRadius, 0, Math.PI * 2);
                this.ctx.stroke();
                this.ctx.globalAlpha = 1.0;
            }
            
            // Outer circle (main target)
            this.ctx.fillStyle = target.color;
            this.ctx.beginPath();
            this.ctx.arc(target.x, target.y, target.radius, 0, Math.PI * 2);
            this.ctx.fill();
            
            // Border
            this.ctx.strokeStyle = 'white';
            this.ctx.lineWidth = 4;
            this.ctx.stroke();
            
            // Inner highlight
            this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
            this.ctx.beginPath();
            this.ctx.arc(target.x - 8, target.y - 8, target.radius * 0.4, 0, Math.PI * 2);
            this.ctx.fill();
            
            // Number (larger and bolder)
            this.ctx.fillStyle = 'white';
            this.ctx.font = 'bold 24px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(target.id, target.x, target.y);
            
            this.ctx.restore();
        }
        
        // Draw trajectory (last 50 events)
        if (this.events.length > 1) {
            this.ctx.strokeStyle = 'rgba(102, 126, 234, 0.3)';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            
            const recentEvents = this.events.slice(-50);
            for (let i = 0; i < recentEvents.length; i++) {
                const event = recentEvents[i];
                if (i === 0) {
                    this.ctx.moveTo(event.x, event.y);
                } else {
                    this.ctx.lineTo(event.x, event.y);
                }
            }
            this.ctx.stroke();
        }
        
        this.animationFrame = requestAnimationFrame(() => this.animate());
    }

    startTimer() {
        document.getElementById('timer').textContent = this.timeRemaining;
        
        this.timerInterval = setInterval(() => {
            this.timeRemaining--;
            document.getElementById('timer').textContent = this.timeRemaining;
            
            if (this.timeRemaining <= 0) {
                this.timeout();
            }
        }, 1000);
    }

    timeout() {
        this.stopChallenge();
        alert('Time expired. Please try again.');
        this.cancelCaptcha();
    }

    async verifyCaptcha() {
        this.stopChallenge();
        clearInterval(this.timerInterval);
        
        // Wait for PoW to complete (with timeout)
        const powTimeout = new Promise((_, reject) => 
            setTimeout(() => reject('PoW timeout'), 30000)
        );
        
        let powProof = this.pow.getProof();
        if (!powProof) {
            try {
                await Promise.race([
                    new Promise(resolve => {
                        const check = setInterval(() => {
                            powProof = this.pow.getProof();
                            if (powProof) {
                                clearInterval(check);
                                resolve();
                            }
                        }, 100);
                    }),
                    powTimeout
                ]);
            } catch (e) {
                alert('Security check timeout. Please try again.');
                this.cancelCaptcha();
                return;
            }
        }
        
        // Collect fingerprint
        const fingerprint = await this.fingerprint.collect();
        
        // Send events to server for verification
        const verificationData = {
            events: this.events,
            targetSequence: this.targetSequence,
            targetsHit: this.targetsHit,
            totalTime: performance.now() - this.startTime,
            canvasWidth: this.canvas.width,
            canvasHeight: this.canvas.height,
            session_id: this.sessionId,
            pow_nonce: powProof.nonce,
            pow_hash: powProof.hash,
            fingerprint: fingerprint
        };
        
        try {
            const response = await fetch('/verify-motor-captcha', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(verificationData)
            });
            
            const result = await response.json();
            console.log('Verification result:', result);
            
            if (result.verified) {
                console.log('Verification successful, showing success screen');
                this.showSuccess();
            } else {
                if (result.escalate) {
                    // Borderline case - show second challenge
                    alert('Verification inconclusive. Please try again.');
                    this.showCaptcha();
                } else {
                    alert(`Verification failed: ${result.reason}`);
                    this.cancelCaptcha();
                }
            }
        } catch (error) {
            console.error('Verification error:', error);
            alert('Verification error. Please try again.');
            this.cancelCaptcha();
        }
    }

    escalateToPuzzle() {
        // Hide motor captcha
        document.getElementById('captchaSection').style.display = 'none';

        // Show puzzle section
        const puzzleSection = document.getElementById('puzzleSection');
        puzzleSection.style.display = 'block';

        // Update puzzle iframe URL to include fingerprint hash for session tracking
        const puzzleFrame = document.getElementById('puzzleFrame');
        if (puzzleFrame && this.fpHash) {
            puzzleFrame.src = `/puzzle?fp=${encodeURIComponent(this.fpHash)}`;
        }

        // Set up message listener for puzzle completion
        window.addEventListener('message', (event) => this.handlePuzzleMessage(event));

        // Add cancel button handler for puzzle
        const cancelBtn = document.getElementById('puzzleCancelBtn');
        if (cancelBtn) {
            cancelBtn.onclick = () => {
                puzzleSection.style.display = 'none';
                document.getElementById('transferSection').style.display = 'block';
                window.removeEventListener('message', this.handlePuzzleMessage);
            };
        }
    }

    handlePuzzleMessage(event) {
        // Handle messages from puzzle iframe
        if (event.data && event.data.type === 'puzzleSolved') {
            console.log(' Puzzle solved! Code:', event.data.code);
            window.removeEventListener('message', this.handlePuzzleMessage);
            document.getElementById('puzzleSection').style.display = 'none';

            // Server resets session on puzzle success
            this.showSuccess();
        }
    }

    showSuccess() {
        const recipient = document.getElementById('recipient').value;
        const amount = document.getElementById('amount').value;

        document.getElementById('captchaSection').style.display = 'none';
        document.getElementById('successSection').style.display = 'block';
        
        document.getElementById('transferDetails').innerHTML = `
            <p><strong>Recipient:</strong> ${recipient}</p>
            <p><strong>Amount:</strong> $${parseFloat(amount).toFixed(2)}</p>
            <p><strong>Status:</strong> Transfer initiated successfully</p>
        `;
    }

    showWrongTargetFeedback(x, y) {
        // Draw a red X at the click location
        this.ctx.save();
        this.ctx.strokeStyle = '#ff4444';
        this.ctx.lineWidth = 4;
        this.ctx.lineCap = 'round';
        
        const size = 15;
        this.ctx.beginPath();
        this.ctx.moveTo(x - size, y - size);
        this.ctx.lineTo(x + size, y + size);
        this.ctx.moveTo(x + size, y - size);
        this.ctx.lineTo(x - size, y + size);
        this.ctx.stroke();
        
        this.ctx.restore();
        
        // The X will be cleared on next animation frame
    }

    stopChallenge() {
        this.isActive = false;
        if (this.pow) {
            this.pow.stop();
        }
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        if (this.targetSpawnInterval) {
            clearTimeout(this.targetSpawnInterval);
        }
    }

    cancelCaptcha() {
        this.stopChallenge();
        clearInterval(this.timerInterval);
        
        document.getElementById('captchaSection').style.display = 'none';
        document.getElementById('transferSection').style.display = 'block';
    }

    resetForm() {
        document.getElementById('successSection').style.display = 'none';
        document.getElementById('transferSection').style.display = 'block';
        document.getElementById('recipient').value = '';
        document.getElementById('amount').value = '';
    }
}

// Initialize CAPTCHA when page loads
let motorCaptcha;
window.addEventListener('DOMContentLoaded', () => {
    motorCaptcha = new MotorTimingCaptcha();

});