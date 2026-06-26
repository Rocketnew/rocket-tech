(function() {
    // ════════════════════════════════════════
    // 🛡️ Stealth JS vv8.0 — Auto-Generated 1782474518
    // ════════════════════════════════════════
    
    // ── 1. Canvas Fingerprint Protection ──
    const __canvasNoise = 1;
    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
        const imageData = origGetImageData.call(this, x, y, w, h);
        for (let i = 0; i < imageData.data.length; i += 4) {
            imageData.data[i] = Math.min(255, Math.max(0, imageData.data[i] + Math.floor(Math.random() * 11 - 3)));
            imageData.data[i+1] = Math.min(255, Math.max(0, imageData.data[i+1] + Math.floor(Math.random() * 11 - 3)));
            imageData.data[i+2] = Math.min(255, Math.max(0, imageData.data[i+2] + Math.floor(Math.random() * 11 - 3)));
        }
        return imageData;
    };
    
    // ── 2. WebGL Vendor/Renderer Spoof ──
    const getParameterProxyHandler = {
        apply: function(target, ctx, args) {
            const param = args[0];
            if (param === 37445) return "Mozilla (Intel)";
            if (param === 37446) return "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)";
            if (param === 3415) return Math.max(0, Math.min(1, 0.67));
            if (param === 3414) return Math.max(0, Math.min(32, 16));
            if (param === 34921) return Math.max(0, Math.min(8, 8));
            return Reflect.apply(target, ctx, args);
        }
   };
    WebGLRenderingContext.prototype.getParameter = new Proxy(WebGLRenderingContext.prototype.getParameter, getParameterProxyHandler);
    WebGL2RenderingContext.prototype.getParameter = new Proxy(WebGL2RenderingContext.prototype.getParameter, getParameterProxyHandler);
    
    // ── 3. Navigator Overrides ──
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
    Object.defineProperty(navigator, 'plugins', { get: () => [{
        0: {type: "application/x-google-chrome-pdf"},
        description: "Chrome PDF Plugin",
        filename: "internal-pdf-viewer",
        length: 1,
        name: "Chrome PDF Plugin",
    }, {
        0: {type: "application/pdf"},
        description: "Chrome PDF Viewer",
        filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
        length: 1,
        name: "Chrome PDF Viewer",
    }], configurable: true });
    Object.defineProperty(navigator, 'languages', { get: () => ["en-IN", "en"], configurable: true });
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 6, configurable: true });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8, configurable: true });
    Object.defineProperty(navigator, 'platform', { get: () => "Android", configurable: true });
    Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5, configurable: true });
    
    // ── 4. Chrome Runtime Override ──
    if (window.chrome) {
        window.chrome.runtime = {
            id: "ad352842aa5fe9c1947bd24ff61816c8",
            connect: () => null,
            sendMessage: () => null,
            getManifest: () => ({ name: "Chrome Media Router", version: "129.0.6668.100" }),
        };
    }
    
    // ── 5. Battery API ──
    if (navigator.getBattery) {
        navigator.getBattery = () => Promise.resolve({
            charging: true,
            chargingTime: 0,
            dischargingTime: 10800,
            level: 0.12,
            onchargingchange: null,
            onchargingtimechange: null,
            ondischargingtimechange: null,
            onlevelchange: null,
        });
    }
    
    // ── 6. Screen Properties ──
    Object.defineProperty(screen, 'availWidth', { get: () => 1366 });
    Object.defineProperty(screen, 'availHeight', { get: () => 768 });
    Object.defineProperty(screen, 'colorDepth', { get: () => 48 });
    Object.defineProperty(screen, 'pixelDepth', { get: () => 30 });
    
    // ── 7. AudioContext Noise ──
    const origGetChannelData = AudioBuffer.prototype.getChannelData;
    AudioBuffer.prototype.getChannelData = function(channel) {
        const data = origGetChannelData.call(this, channel);
        for (let i = 0; i < data.length; i += Math.floor(Math.random() * 100) + 50) {
            data[i] += (Math.random() - 0.5) * 3.633e-05;
        }
        return data;
    };
    
    // ── 8. Permissions ──
    const origQuery = navigator.permissions.query;
    navigator.permissions.query = (desc) => {
        if (desc.name === 'notifications') return Promise.resolve({state: 'prompt'});
        if (desc.name === 'clipboard-read') return Promise.resolve({state: 'denied'});
        if (desc.name === 'clipboard-write') return Promise.resolve({state: 'granted'});
        return origQuery.call(navigator.permissions, desc);
    };
    
    // ── 9. Font Detection Protection ──
    const origMeasureText = CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText = function(text) {
        const metrics = origMeasureText.call(this, text);
        metrics.width += (Math.random() - 0.5) * 0.3;
        return metrics;
    };
    
    // ── 10. Timezone/Locale Spoof ──
    Object.defineProperty(Intl.DateTimeFormat.prototype, 'resolvedOptions', {
        value: function() {
            return {
                locale: "en-AU",
                calendar: "gregorian",
                numberingSystem: "latn",
                timeZone: "America/Chicago",
            };
        }
    });
})();
