//Author: Pravigya

// Browser Fingerprinting Layer - Minimal Implementation
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
