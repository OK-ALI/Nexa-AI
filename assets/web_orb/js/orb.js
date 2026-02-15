/**
 * NEXA Particle Orb - Phase 17
 * A voice-reactive particle orb visualization for NEXA AI Assistant.
 * States: idle, listening, thinking, responding, error
 * Reacts to audio amplitude in real-time.
 */

(function () {
    "use strict";

    // ── Canvas Setup ──────────────────────────────────────────────
    const canvas = document.getElementById("orbCanvas");
    const ctx = canvas.getContext("2d");
    let W, H, centerX, centerY, orbRadius;

    function resize() {
        const dpr = window.devicePixelRatio || 1;
        W = canvas.clientWidth;
        H = canvas.clientHeight;
        canvas.width = W * dpr;
        canvas.height = H * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        centerX = W / 2;
        centerY = H / 2;
        orbRadius = Math.min(W, H) * 0.18;
    }
    window.addEventListener("resize", resize);
    resize();

    // ── Theme Colors ──────────────────────────────────────────────
    const THEMES = {
        dark: {
            idle:       { primary: "#0088CC", glow: "rgba(0,136,204,0.35)",  ring: "rgba(0,136,204,0.18)" },
            listening:  { primary: "#00D4FF", glow: "rgba(0,212,255,0.45)",  ring: "rgba(0,212,255,0.22)" },
            thinking:   { primary: "#9F7FFF", glow: "rgba(159,127,255,0.40)", ring: "rgba(159,127,255,0.20)" },
            responding: { primary: "#00FF96", glow: "rgba(0,255,150,0.40)",  ring: "rgba(0,255,150,0.20)" },
            error:      { primary: "#FF4757", glow: "rgba(255,71,87,0.45)",  ring: "rgba(255,71,87,0.22)" }
        },
        light: {
            idle:       { primary: "#4477AA", glow: "rgba(68,119,170,0.30)",  ring: "rgba(68,119,170,0.15)" },
            listening:  { primary: "#005A99", glow: "rgba(0,90,153,0.35)",    ring: "rgba(0,90,153,0.18)" },
            thinking:   { primary: "#5B48CE", glow: "rgba(91,72,206,0.35)",   ring: "rgba(91,72,206,0.18)" },
            responding: { primary: "#008855", glow: "rgba(0,136,85,0.35)",    ring: "rgba(0,136,85,0.18)" },
            error:      { primary: "#BB1122", glow: "rgba(187,17,34,0.40)",   ring: "rgba(187,17,34,0.20)" }
        }
    };

    // ── State ─────────────────────────────────────────────────────
    let currentState = "idle";
    let currentTheme = "dark";
    let audioLevel = 0;            // 0.0 – 1.0
    let smoothAudio = 0;           // smoothed amplitude
    let targetColor = { r: 0, g: 136, b: 204 };
    let currentColor = { r: 0, g: 136, b: 204 };
    let time = 0;

    // ── Smooth Behavior Params (interpolated per-frame) ───────────
    const STATE_BEHAVIORS = {
        idle:       { speed: 0.3, spread: 1.0,  pulse: 0.15, swirlAlpha: 0.0 },
        listening:  { speed: 0.7, spread: 1.3,  pulse: 0.6,  swirlAlpha: 0.0 },
        thinking:   { speed: 0.8, spread: 1.15, pulse: 0.3,  swirlAlpha: 1.0 },
        responding: { speed: 0.9, spread: 1.1,  pulse: 0.5,  swirlAlpha: 0.0 },
        error:      { speed: 1.5, spread: 1.6,  pulse: 0.8,  swirlAlpha: 0.0 }
    };
    // Current interpolated behavior (starts at idle)
    let currentBehavior = { speed: 0.3, spread: 1.0, pulse: 0.15, swirlAlpha: 0.0 };

    // ── Simulated audio for responding state ──────────────────────
    let simulatedAudio = 0;
    let simPhase = 0;

    // ── Particles ─────────────────────────────────────────────────
    const MAX_PARTICLES = 140;
    let particles = [];

    class Particle {
        constructor() {
            this.reset();
        }

        reset() {
            // spawn in a ring around the orb center
            const angle = Math.random() * Math.PI * 2;
            const dist = orbRadius * (0.3 + Math.random() * 1.2);
            this.x = centerX + Math.cos(angle) * dist;
            this.y = centerY + Math.sin(angle) * dist;
            this.baseX = this.x;
            this.baseY = this.y;
            this.vx = (Math.random() - 0.5) * 0.4;
            this.vy = (Math.random() - 0.5) * 0.4;
            this.radius = 1 + Math.random() * 2.5;
            this.baseRadius = this.radius;
            this.life = 0.6 + Math.random() * 0.4;   // 0-1 opacity factor
            this.angle = angle;
            this.orbitSpeed = (Math.random() - 0.5) * 0.003;
            this.orbitRadius = dist;
            this.phase = Math.random() * Math.PI * 2;
        }

        update(dt) {
            const sm = currentBehavior; // uses smoothly interpolated params

            // Orbit
            this.angle += this.orbitSpeed * sm.speed * dt * 60;

            // Audio reactivity
            const audioPush = smoothAudio * sm.pulse * orbRadius * 0.5;
            const targetDist = this.orbitRadius * sm.spread + audioPush;

            this.x = centerX + Math.cos(this.angle) * targetDist + Math.sin(time * 0.5 + this.phase) * 3 * sm.speed;
            this.y = centerY + Math.sin(this.angle) * targetDist + Math.cos(time * 0.7 + this.phase) * 3 * sm.speed;

            // Pulsing radius
            this.radius = this.baseRadius * (1 + smoothAudio * sm.pulse * 1.5 + Math.sin(time * 2 + this.phase) * 0.2);

            // Breathing opacity
            this.life = 0.4 + 0.3 * Math.sin(time * 1.5 + this.phase) + smoothAudio * 0.3;
            this.life = Math.min(1, Math.max(0.1, this.life));
        }

        draw() {
            const alpha = this.life * 0.85;
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${currentColor.r},${currentColor.g},${currentColor.b},${alpha})`;
            ctx.fill();
        }
    }

    function initParticles() {
        particles = [];
        for (let i = 0; i < MAX_PARTICLES; i++) {
            particles.push(new Particle());
        }
    }

    // ── Energy Ring Waves ─────────────────────────────────────────
    const MAX_RINGS = 5;
    let rings = [];

    class EnergyRing {
        constructor(radius) {
            this.radius = radius;
            this.maxRadius = orbRadius * 2.8;
            this.life = 1.0;
            this.speed = 0.6 + smoothAudio * 1.5;
        }

        update(dt) {
            this.radius += this.speed * dt * 60;
            this.life = 1.0 - (this.radius / this.maxRadius);
            if (this.life < 0) this.life = 0;
        }

        draw() {
            if (this.life <= 0) return;
            const alpha = this.life * 0.3;
            ctx.beginPath();
            ctx.arc(centerX, centerY, this.radius, 0, Math.PI * 2);
            ctx.strokeStyle = `rgba(${currentColor.r},${currentColor.g},${currentColor.b},${alpha})`;
            ctx.lineWidth = 1.5 * this.life;
            ctx.stroke();
        }
    }

    let ringTimer = 0;
    function updateRings(dt) {
        // Ring interval scales with behavior speed (faster = more frequent)
        const baseInterval = 2.5;
        const interval = Math.max(0.3, baseInterval / (0.5 + currentBehavior.speed));

        ringTimer += dt;
        if (ringTimer >= interval && rings.length < MAX_RINGS) {
            rings.push(new EnergyRing(orbRadius * 0.6));
            ringTimer = 0;
        }

        // Also spawn on audio spikes
        if (smoothAudio > 0.5 && rings.length < MAX_RINGS && Math.random() < 0.08) {
            rings.push(new EnergyRing(orbRadius * 0.5));
        }

        rings.forEach(r => r.update(dt));
        rings = rings.filter(r => r.life > 0);
    }

    // ── Connection Lines (optimized: batch path + skip particles) ──
    function drawConnections() {
        const maxDist = orbRadius * 0.9 + smoothAudio * orbRadius * 0.4;
        const maxDistSq = maxDist * maxDist; // avoid sqrt
        const step = 3; // check every 3rd particle pair

        ctx.strokeStyle = `rgba(${currentColor.r},${currentColor.g},${currentColor.b},0.08)`;
        ctx.lineWidth = 0.5;
        ctx.beginPath(); // single batched path

        for (let i = 0; i < particles.length; i += step) {
            for (let j = i + step; j < particles.length; j += step) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const distSq = dx * dx + dy * dy;
                if (distSq < maxDistSq) {
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                }
            }
        }
        ctx.stroke(); // one single draw call
    }

    // ── Central Orb Glow ──────────────────────────────────────────
    function drawCoreGlow() {
        const colors = THEMES[currentTheme][currentState] || THEMES[currentTheme].idle;
        const pulseScale = 1 + smoothAudio * 0.25 + Math.sin(time * 2) * 0.05;
        const coreRadius = orbRadius * 0.45 * pulseScale;

        // Outer glow
        const gradient = ctx.createRadialGradient(
            centerX, centerY, coreRadius * 0.2,
            centerX, centerY, orbRadius * 1.6
        );
        gradient.addColorStop(0, colors.glow);
        gradient.addColorStop(0.4, colors.ring);
        gradient.addColorStop(1, "rgba(0,0,0,0)");

        ctx.beginPath();
        ctx.arc(centerX, centerY, orbRadius * 1.6, 0, Math.PI * 2);
        ctx.fillStyle = gradient;
        ctx.fill();

        // Bright core
        const coreGrad = ctx.createRadialGradient(
            centerX, centerY, 0,
            centerX, centerY, coreRadius
        );
        coreGrad.addColorStop(0, `rgba(255,255,255,${0.15 + smoothAudio * 0.15})`);
        coreGrad.addColorStop(0.5, `rgba(${currentColor.r},${currentColor.g},${currentColor.b},${0.25 + smoothAudio * 0.2})`);
        coreGrad.addColorStop(1, `rgba(${currentColor.r},${currentColor.g},${currentColor.b},0)`);

        ctx.beginPath();
        ctx.arc(centerX, centerY, coreRadius, 0, Math.PI * 2);
        ctx.fillStyle = coreGrad;
        ctx.fill();
    }

    // ── Audio Waveform Ring (listening/responding) ─────────────────
    function drawWaveformRing() {
        if (currentState !== "listening" && currentState !== "responding") return;
        if (smoothAudio < 0.02) return;

        const segments = 64;
        const baseRadius = orbRadius * 0.85;

        ctx.beginPath();
        for (let i = 0; i <= segments; i++) {
            const angle = (i / segments) * Math.PI * 2;
            const wave = Math.sin(angle * 8 + time * 4) * smoothAudio * orbRadius * 0.2;
            const r = baseRadius + wave;
            const x = centerX + Math.cos(angle) * r;
            const y = centerY + Math.sin(angle) * r;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = `rgba(${currentColor.r},${currentColor.g},${currentColor.b},${0.2 + smoothAudio * 0.3})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
    }

    // ── Thinking Swirl ────────────────────────────────────────────
    function drawThinkingSwirl() {
        if (currentBehavior.swirlAlpha < 0.01) return; // smoothly faded out
        const arms = 3;
        for (let a = 0; a < arms; a++) {
            ctx.beginPath();
            const armOffset = (a / arms) * Math.PI * 2;
            for (let i = 0; i < 60; i++) {
                const t = i / 60;
                const angle = armOffset + t * Math.PI * 3 + time * 1.5;
                const r = orbRadius * (0.3 + t * 1.0);
                const x = centerX + Math.cos(angle) * r;
                const y = centerY + Math.sin(angle) * r;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            const alpha = (0.1 + smoothAudio * 0.15) * currentBehavior.swirlAlpha;
            ctx.strokeStyle = `rgba(${currentColor.r},${currentColor.g},${currentColor.b},${alpha})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }
    }

    // ── Color Interpolation ───────────────────────────────────────
    function hexToRgb(hex) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return { r, g, b };
    }

    function lerpColor(from, to, t) {
        return {
            r: Math.round(from.r + (to.r - from.r) * t),
            g: Math.round(from.g + (to.g - from.g) * t),
            b: Math.round(from.b + (to.b - from.b) * t)
        };
    }

    // ── Main Loop ─────────────────────────────────────────────────
    let lastTime = performance.now();

    function lerp(a, b, t) { return a + (b - a) * t; }

    function animate(now) {
        const dt = Math.min((now - lastTime) / 1000, 0.05); // cap at 50ms
        lastTime = now;
        time += dt;

        // ── Smoothly interpolate behavior params toward target state ──
        const targetBehavior = STATE_BEHAVIORS[currentState] || STATE_BEHAVIORS.idle;
        const behaviorLerp = 1 - Math.pow(0.05, dt); // ~3-4x/sec smooth blend
        currentBehavior.speed     = lerp(currentBehavior.speed,     targetBehavior.speed,     behaviorLerp);
        currentBehavior.spread    = lerp(currentBehavior.spread,    targetBehavior.spread,    behaviorLerp);
        currentBehavior.pulse     = lerp(currentBehavior.pulse,     targetBehavior.pulse,     behaviorLerp);
        currentBehavior.swirlAlpha = lerp(currentBehavior.swirlAlpha, targetBehavior.swirlAlpha, behaviorLerp);

        // ── Simulated audio for responding state (TTS speech sync) ──
        if (currentState === "responding") {
            // Generate organic speech-like amplitude pattern
            simPhase += dt * 7.5;
            simulatedAudio = 0.35
                + 0.25 * Math.sin(simPhase * 1.0)
                + 0.15 * Math.sin(simPhase * 2.3 + 1.2)
                + 0.10 * Math.sin(simPhase * 5.7 + 0.5)
                + 0.08 * Math.sin(simPhase * 11.3 + 2.1);
            simulatedAudio = Math.max(0.15, Math.min(1, simulatedAudio));
        } else {
            // Fade out simulated audio when leaving responding
            simulatedAudio *= Math.pow(0.02, dt);
        }

        // Use whichever audio source is active
        const effectiveAudio = Math.max(audioLevel, simulatedAudio);

        // Smooth audio (fast attack, slow release)
        const attackSpeed = 12;
        const releaseSpeed = 4;
        if (effectiveAudio > smoothAudio) {
            smoothAudio += (effectiveAudio - smoothAudio) * attackSpeed * dt;
        } else {
            smoothAudio += (effectiveAudio - smoothAudio) * releaseSpeed * dt;
        }
        smoothAudio = Math.max(0, Math.min(1, smoothAudio));

        // Smooth color transition
        const themeColors = THEMES[currentTheme][currentState] || THEMES[currentTheme].idle;
        targetColor = hexToRgb(themeColors.primary);
        currentColor = lerpColor(currentColor, targetColor, 3 * dt);

        // Clear
        ctx.clearRect(0, 0, W, H);

        // Draw layers (back to front)
        drawCoreGlow();
        updateRings(dt);
        rings.forEach(r => r.draw());
        drawThinkingSwirl();
        drawConnections();
        particles.forEach(p => { p.update(dt); p.draw(); });
        drawWaveformRing();

        requestAnimationFrame(animate);
    }

    // ── Public API (called from Python via QWebChannel) ───────────
    window.updateOrbState = function (state) {
        const validStates = ["idle", "listening", "thinking", "responding", "error"];
        if (validStates.includes(state)) {
            currentState = state;
        }
    };

    window.updateAudioLevel = function (level) {
        audioLevel = Math.max(0, Math.min(1, level));
    };

    window.updateTheme = function (theme) {
        if (theme === "dark" || theme === "light") {
            currentTheme = theme;
        }
    };

    window.setThemeColors = function (colorsJson) {
        try {
            const colors = JSON.parse(colorsJson);
            // Allow dynamic color override: { idle: "#hex", listening: "#hex", ... }
            for (const state in colors) {
                if (THEMES[currentTheme][state]) {
                    const hex = colors[state];
                    const rgb = hexToRgb(hex);
                    THEMES[currentTheme][state].primary = hex;
                    THEMES[currentTheme][state].glow = `rgba(${rgb.r},${rgb.g},${rgb.b},0.40)`;
                    THEMES[currentTheme][state].ring = `rgba(${rgb.r},${rgb.g},${rgb.b},0.20)`;
                }
            }
        } catch (e) { /* ignore parse errors */ }
    };

    // ── Initialize ────────────────────────────────────────────────
    initParticles();
    requestAnimationFrame(animate);

    // Re-init particles on resize
    window.addEventListener("resize", function () {
        resize();
        initParticles();
    });

    // Signal ready
    window._orbReady = true;
    if (window._onOrbReady) window._onOrbReady();
})();
