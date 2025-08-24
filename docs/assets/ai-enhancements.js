/* Studiorum Documentation - AI Enhancements JavaScript
 * Generated from private/docs-mkdocs.md plan on 2025-08-24
 * Subtle AI-influenced visual effects and tech elements
 */

(function() {
    'use strict';

    // Check user preferences
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const prefersReducedData = window.matchMedia('(prefers-reduced-data: reduce)').matches;

    /* =========================================================================
       AI VISUAL EFFECTS INITIALIZATION
       ========================================================================= */

    /**
     * Initialize AI-themed enhancements
     */
    function initializeAIEnhancements() {
        console.log('🤖 Initializing AI visual enhancements');

        if (prefersReducedMotion || prefersReducedData) {
            console.log('⚡ Reduced motion/data mode - minimal effects only');
            setupMinimalEffects();
            return;
        }

        setupMatrixRain();
        setupParticleField();
        // setupCodeGlitchEffect(); // Disabled: causes white flashing in code blocks
        // setupAIGlowPulse(); // Disabled: causes white flashing in code blocks
        setupDataStreamEffects();
        setupHologramBorders();
        setupTypingAnimations();

        console.log('✨ AI enhancements initialized');
    }

    /* =========================================================================
       MATRIX RAIN EFFECT (SUBTLE)
       ========================================================================= */

    /**
     * Create subtle matrix rain effect for hero backgrounds
     */
    function setupMatrixRain() {
        const hero = document.querySelector('.hero-banner');
        if (!hero) return;

        const canvas = document.createElement('canvas');
        canvas.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            opacity: 0.1;
            z-index: -1;
        `;

        hero.appendChild(canvas);
        hero.style.position = 'relative';

        const ctx = canvas.getContext('2d');

        function resizeCanvas() {
            canvas.width = hero.offsetWidth;
            canvas.height = hero.offsetHeight;
        }

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // Matrix characters (D&D themed)
        const chars = '⚔️🛡️🏹🧙‍♂️🐉📜🎲⚡🔮🗡️';
        const charArray = Array.from(chars);

        const drops = [];
        const fontSize = 14;
        const columns = Math.floor(canvas.width / fontSize);

        // Initialize drops
        for (let i = 0; i < columns; i++) {
            drops[i] = Math.random() * -100;
        }

        function drawMatrix() {
            ctx.fillStyle = 'rgba(26, 10, 46, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.fillStyle = '#4a148c';
            ctx.font = fontSize + 'px monospace';

            for (let i = 0; i < drops.length; i++) {
                const char = charArray[Math.floor(Math.random() * charArray.length)];
                const x = i * fontSize;
                const y = drops[i] * fontSize;

                ctx.fillText(char, x, y);

                drops[i]++;
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.98) {
                    drops[i] = 0;
                }
            }
        }

        // Animate at 30fps for performance
        setInterval(drawMatrix, 100);
    }

    /* =========================================================================
       PARTICLE FIELD EFFECT
       ========================================================================= */

    /**
     * Create floating particle field for tech atmosphere
     * Disabled for feature-cards to avoid grid layout interference
     */
    function setupParticleField() {
        const containers = document.querySelectorAll('.hero-banner');
        if (containers.length === 0) return;

        containers.forEach(container => {
            createParticleField(container);
        });
    }

    function createParticleField(container) {
        const canvas = document.createElement('canvas');
        canvas.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            opacity: 0.3;
            z-index: 0;
        `;

        container.appendChild(canvas);
        container.style.position = 'relative';

        const ctx = canvas.getContext('2d');
        const particles = [];

        function resizeCanvas() {
            canvas.width = container.offsetWidth;
            canvas.height = container.offsetHeight;
            initParticles();
        }

        function initParticles() {
            particles.length = 0;
            const particleCount = Math.min(50, Math.floor((canvas.width * canvas.height) / 10000));

            for (let i = 0; i < particleCount; i++) {
                particles.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    vx: (Math.random() - 0.5) * 0.5,
                    vy: (Math.random() - 0.5) * 0.5,
                    size: Math.random() * 2 + 0.5,
                    opacity: Math.random() * 0.5 + 0.2
                });
            }
        }

        function animateParticles() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            particles.forEach(particle => {
                particle.x += particle.vx;
                particle.y += particle.vy;

                // Bounce off edges
                if (particle.x <= 0 || particle.x >= canvas.width) particle.vx *= -1;
                if (particle.y <= 0 || particle.y >= canvas.height) particle.vy *= -1;

                // Draw particle
                ctx.beginPath();
                ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(0, 229, 255, ${particle.opacity})`;
                ctx.fill();

                // Draw connections to nearby particles
                particles.forEach(other => {
                    const dx = particle.x - other.x;
                    const dy = particle.y - other.y;
                    const distance = Math.sqrt(dx * dx + dy * dy);

                    if (distance < 100) {
                        ctx.beginPath();
                        ctx.moveTo(particle.x, particle.y);
                        ctx.lineTo(other.x, other.y);
                        ctx.strokeStyle = `rgba(0, 229, 255, ${0.1 * (1 - distance / 100)})`;
                        ctx.stroke();
                    }
                });
            });

            requestAnimationFrame(animateParticles);
        }

        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);
        animateParticles();
    }

    /* =========================================================================
       CODE GLITCH EFFECT
       ========================================================================= */

    /**
     * Add subtle glitch effects to code blocks
     */
    function setupCodeGlitchEffect() {
        const codeBlocks = document.querySelectorAll('pre code');

        codeBlocks.forEach(block => {
            // Add glitch effect on hover
            block.addEventListener('mouseenter', function() {
                if (Math.random() < 0.3) { // Only 30% chance to avoid being annoying
                    applyGlitchEffect(this);
                }
            });
        });
    }

    function applyGlitchEffect(element) {
        const originalText = element.textContent;
        const glitchChars = '!<>-_\\/[]{}—=+*^?#________';

        let glitchText = originalText;
        const iterations = 3;
        let currentIteration = 0;

        const glitchInterval = setInterval(() => {
            glitchText = originalText.split('').map((char, index) => {
                if (Math.random() < 0.02 && char !== ' ') {
                    return glitchChars[Math.floor(Math.random() * glitchChars.length)];
                }
                return char;
            }).join('');

            element.textContent = glitchText;
            currentIteration++;

            if (currentIteration >= iterations) {
                element.textContent = originalText;
                clearInterval(glitchInterval);
            }
        }, 50);
    }

    /* =========================================================================
       AI GLOW PULSE
       ========================================================================= */

    /**
     * Setup pulsing glow effects for AI elements
     */
    function setupAIGlowPulse() {
        const glowElements = document.querySelectorAll('.btn-accent, code, .status-indicator');

        glowElements.forEach(element => {
            element.style.transition = 'all 0.3s ease';

            // Random pulse timing to avoid synchronization
            const pulseInterval = 2000 + Math.random() * 2000;

            setInterval(() => {
                if (Math.random() < 0.5) { // 50% chance to pulse
                    element.style.filter = 'brightness(1.2) drop-shadow(0 0 8px rgba(0, 229, 255, 0.6))';

                    setTimeout(() => {
                        element.style.filter = '';
                    }, 300);
                }
            }, pulseInterval);
        });
    }

    /* =========================================================================
       DATA STREAM EFFECTS
       ========================================================================= */

    /**
     * Create data stream animations for navigation
     */
    function setupDataStreamEffects() {
        const navItems = document.querySelectorAll('.navbar-nav > li > a');

        navItems.forEach(item => {
            item.addEventListener('mouseenter', function() {
                createDataStream(this);
            });
        });
    }

    function createDataStream(element) {
        const stream = document.createElement('div');
        stream.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg,
                transparent,
                var(--studiorum-cyan-glow),
                transparent);
            animation: dataFlow 0.8s ease-in-out;
        `;

        // Add keyframes if not already added
        if (!document.getElementById('data-stream-styles')) {
            const style = document.createElement('style');
            style.id = 'data-stream-styles';
            style.textContent = `
                @keyframes dataFlow {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
                }
            `;
            document.head.appendChild(style);
        }

        element.style.position = 'relative';
        element.style.overflow = 'hidden';
        element.appendChild(stream);

        // Remove stream after animation
        setTimeout(() => {
            stream.remove();
        }, 800);
    }

    /* =========================================================================
       HOLOGRAM BORDERS
       ========================================================================= */

    /**
     * Add hologram-style border effects
     * Disabled for feature cards to prevent grid layout issues
     */
    function setupHologramBorders() {
        // Disabled: const cards = document.querySelectorAll('.feature-cards > *');
        // Feature cards now use simpler CSS-only hover effects
        console.log('Hologram borders disabled for grid layout stability');
    }

    function addHologramBorder(element) {
        const border = document.createElement('div');
        border.className = 'hologram-border';
        border.style.cssText = `
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            border: 2px solid var(--studiorum-cyan-glow);
            border-radius: inherit;
            opacity: 0;
            animation: hologramFadeIn 0.3s ease forwards;
            pointer-events: none;
        `;

        // Add keyframes if not already added
        if (!document.getElementById('hologram-styles')) {
            const style = document.createElement('style');
            style.id = 'hologram-styles';
            style.textContent = `
                @keyframes hologramFadeIn {
                    to { opacity: 0.8; }
                }
                @keyframes hologramFadeOut {
                    to { opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }

        element.style.position = 'relative';
        element.appendChild(border);
    }

    function removeHologramBorder(element) {
        const border = element.querySelector('.hologram-border');
        if (border) {
            border.style.animation = 'hologramFadeOut 0.3s ease forwards';
            setTimeout(() => border.remove(), 300);
        }
    }

    /* =========================================================================
       TYPING ANIMATIONS
       ========================================================================= */

    /**
     * Add typing animation to specific elements
     */
    function setupTypingAnimations() {
        const typingElements = document.querySelectorAll('[data-typing]');

        typingElements.forEach(element => {
            const text = element.dataset.typing || element.textContent;
            element.textContent = '';
            typeText(element, text);
        });
    }

    function typeText(element, text) {
        let index = 0;
        const cursor = '|';

        function type() {
            if (index < text.length) {
                element.textContent = text.substring(0, index + 1) + cursor;
                index++;
                setTimeout(type, 100 + Math.random() * 100); // Variable typing speed
            } else {
                // Flash cursor a few times then remove
                let flashes = 0;
                const flashInterval = setInterval(() => {
                    element.textContent = text + (flashes % 2 === 0 ? cursor : '');
                    flashes++;
                    if (flashes > 6) {
                        element.textContent = text;
                        clearInterval(flashInterval);
                    }
                }, 500);
            }
        }

        type();
    }

    /* =========================================================================
       MINIMAL EFFECTS (REDUCED MOTION/DATA)
       ========================================================================= */

    /**
     * Setup minimal effects for users who prefer reduced motion/data
     */
    function setupMinimalEffects() {
        // Simple focus indicators
        const interactiveElements = document.querySelectorAll('button, a, input, textarea');

        interactiveElements.forEach(element => {
            element.addEventListener('focus', function() {
                this.style.outline = '2px solid var(--studiorum-cyan-glow)';
                this.style.outlineOffset = '2px';
            });

            element.addEventListener('blur', function() {
                this.style.outline = 'none';
            });
        });

        // Simple hover effects
        const cards = document.querySelectorAll('.feature-cards > *');
        cards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.borderColor = 'var(--studiorum-cyan-glow)';
            });

            card.addEventListener('mouseleave', function() {
                this.style.borderColor = 'var(--studiorum-gold)';
            });
        });
    }

    /* =========================================================================
       PERFORMANCE MONITORING
       ========================================================================= */

    /**
     * Monitor performance and adjust effects accordingly
     */
    function monitorPerformance() {
        let frameCount = 0;
        let lastTime = performance.now();

        function checkPerformance() {
            frameCount++;
            const currentTime = performance.now();

            if (currentTime - lastTime >= 1000) {
                const fps = frameCount;
                frameCount = 0;
                lastTime = currentTime;

                // If FPS is too low, disable heavy effects
                if (fps < 30) {
                    console.warn('🐌 Low FPS detected, disabling heavy AI effects');
                    disableHeavyEffects();
                }
            }

            requestAnimationFrame(checkPerformance);
        }

        requestAnimationFrame(checkPerformance);
    }

    /**
     * Disable heavy effects for performance
     */
    function disableHeavyEffects() {
        // Remove canvas elements
        document.querySelectorAll('canvas').forEach(canvas => {
            if (canvas.parentElement) {
                canvas.remove();
            }
        });

        // Disable complex animations
        const style = document.createElement('style');
        style.textContent = `
            .ai-accent,
            .status-indicator {
                animation: none !important;
            }
        `;
        document.head.appendChild(style);
    }

    /* =========================================================================
       INITIALIZATION
       ========================================================================= */

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeAIEnhancements);
    } else {
        initializeAIEnhancements();
    }

    // Start performance monitoring
    if (!prefersReducedMotion && !prefersReducedData) {
        monitorPerformance();
    }

    // Clean up on page unload
    window.addEventListener('beforeunload', function() {
        // Clear any intervals or timeouts
        // This helps prevent memory leaks in SPAs
    });

})();
