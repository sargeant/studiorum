/* Studiorum Documentation - Theme Interactions JavaScript
 * Generated from private/docs-mkdocs.md plan on 2025-08-24
 * Hover effects, animations, and interactive elements
 */

(function() {
    'use strict';

    // Check if user prefers reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    /* =========================================================================
       INITIALIZATION & SETUP
       ========================================================================= */

    /**
     * Initialize theme interactions when DOM is ready
     */
    function initializeTheme() {
        console.log('🎨 Initializing Studiorum theme interactions');

        setupCardInteractions();
        setupButtonEnhancements();
        setupNavigationEffects();
        setupCodeBlockEnhancements();
        setupScrollEffects();
        setupKeyboardNavigation();

        if (!prefersReducedMotion) {
            // setupAnimationObserver(); // Disabled - was causing header disappearing issues
            setupParallaxEffects();
        }

        console.log('✨ Studiorum theme interactions initialized');
    }

    /* =========================================================================
       FEATURE CARD INTERACTIONS
       ========================================================================= */

    /**
     * Enhance feature cards with simple, grid-safe interactive effects
     */
    function setupCardInteractions() {
        const cards = document.querySelectorAll('.feature-cards > *');

        cards.forEach(card => {
            // Add card interaction class
            card.classList.add('interactive-card');

            // Simple hover effects that won't interfere with grid layout
            card.addEventListener('mouseenter', function() {
                if (!prefersReducedMotion) {
                    // Only use simple translation, no scaling that affects layout
                    this.style.transform = 'translateY(-2px)';
                    this.style.transition = 'all 0.2s ease-out';
                    this.style.boxShadow = '0 8px 25px rgba(255, 193, 7, 0.3)';
                }
            });

            card.addEventListener('mouseleave', function() {
                if (!prefersReducedMotion) {
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = '';
                }
            });

            // Remove click ripple effect to avoid layout interference
            // Simple focus handling for accessibility
            card.addEventListener('focus', function() {
                this.style.outline = '2px solid var(--studiorum-cyan-glow)';
                this.style.outlineOffset = '4px';
            });

            card.addEventListener('blur', function() {
                this.style.outline = 'none';
            });
        });
    }

    // Ripple effect removed to prevent grid layout interference

    /* =========================================================================
       BUTTON ENHANCEMENTS
       ========================================================================= */

    /**
     * Enhance buttons with interactive feedback
     */
    function setupButtonEnhancements() {
        const buttons = document.querySelectorAll('.btn-primary, .btn-secondary, .btn-accent, .btn-outline');

        buttons.forEach(button => {
            // Add loading state capability
            button.addEventListener('click', function() {
                if (this.dataset.loading !== 'true') {
                    addLoadingState(this);
                }
            });

            // Enhanced focus states
            button.addEventListener('focus', function() {
                if (!prefersReducedMotion) {
                    this.style.transform = 'translateY(-1px)';
                    this.style.boxShadow = '0 6px 16px rgba(0, 229, 255, 0.3)';
                }
            });

            button.addEventListener('blur', function() {
                if (!prefersReducedMotion) {
                    this.style.transform = '';
                    this.style.boxShadow = '';
                }
            });
        });
    }

    /**
     * Add loading state to button
     */
    function addLoadingState(button) {
        const originalText = button.textContent;
        button.dataset.loading = 'true';
        button.disabled = true;

        // Add spinner
        button.innerHTML = `
            <span class="loading-spinner" style="
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255,255,255,0.3);
                border-top: 2px solid currentColor;
                border-radius: 50%;
                display: inline-block;
                animation: spin 1s linear infinite;
                margin-right: 8px;
            "></span>
            ${originalText}
        `;

        // Remove loading state after 2 seconds (demo)
        setTimeout(() => {
            button.innerHTML = originalText;
            button.disabled = false;
            button.dataset.loading = 'false';
        }, 2000);
    }

    /* =========================================================================
       NAVIGATION EFFECTS
       ========================================================================= */

    /**
     * Enhance navigation with dynamic effects
     */
    function setupNavigationEffects() {
        const navItems = document.querySelectorAll('.navbar-nav > li > a');

        navItems.forEach(item => {
            // Add active state visual enhancement
            if (item.classList.contains('active') || item.parentElement.classList.contains('active')) {
                if (!prefersReducedMotion) {
                    item.style.background = 'linear-gradient(135deg, rgba(255,193,7,0.2), rgba(0,229,255,0.1))';
                }
            }

            // Smooth scroll for anchor links
            const href = item.getAttribute('href');
            if (href && href.startsWith('#')) {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    const targetId = this.getAttribute('href').substring(1);
                    const targetElement = document.getElementById(targetId);

                    if (targetElement) {
                        targetElement.scrollIntoView({
                            behavior: prefersReducedMotion ? 'auto' : 'smooth',
                            block: 'start'
                        });
                    }
                });
            }
        });

        // Add scroll indicator for long pages
        addScrollIndicator();
    }

    /**
     * Add scroll progress indicator
     */
    function addScrollIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'scroll-indicator';
        indicator.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 0%;
            height: 3px;
            background: linear-gradient(90deg, var(--studiorum-cyan-glow), var(--studiorum-gold));
            z-index: 1000;
            transition: width 0.1s ease-out;
        `;

        document.body.appendChild(indicator);

        // Update indicator on scroll
        window.addEventListener('scroll', function() {
            const scrolled = (window.pageYOffset / (document.documentElement.scrollHeight - window.innerHeight)) * 100;
            indicator.style.width = scrolled + '%';
        });
    }

    /* =========================================================================
       CODE BLOCK ENHANCEMENTS
       ========================================================================= */

    /**
     * Enhance code blocks with interactive features
     */
    function setupCodeBlockEnhancements() {
        const codeBlocks = document.querySelectorAll('pre');

        codeBlocks.forEach(block => {
            // Add copy button
            addCopyButton(block);

            // Language labels disabled - were irritating per user feedback
            /*
            const code = block.querySelector('code');
            if (code && code.className) {
                const language = code.className.replace('language-', '').replace('highlight-', '');
                addLanguageLabel(block, language);
            }
            */

            // Line numbers removed - were causing alignment issues
        });
    }

    /**
     * Add copy button to code block
     */
    function addCopyButton(codeBlock) {
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-code-button';
        copyButton.innerHTML = '📋 Copy';
        copyButton.style.cssText = `
            position: absolute;
            top: 8px;
            right: 8px;
            background: var(--studiorum-deep-purple);
            color: var(--studiorum-gold);
            border: 1px solid var(--studiorum-gold);
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.2s ease;
        `;

        // Make code block relative for absolute positioning
        codeBlock.style.position = 'relative';

        // Show/hide copy button on hover
        codeBlock.addEventListener('mouseenter', () => {
            copyButton.style.opacity = '1';
        });

        codeBlock.addEventListener('mouseleave', () => {
            copyButton.style.opacity = '0';
        });

        // Copy functionality
        copyButton.addEventListener('click', async function() {
            try {
                await navigator.clipboard.writeText(codeBlock.textContent);
                this.innerHTML = '✅ Copied!';
                this.style.background = 'var(--studiorum-success)';

                setTimeout(() => {
                    this.innerHTML = '📋 Copy';
                    this.style.background = 'var(--studiorum-deep-purple)';
                }, 2000);
            } catch (err) {
                console.warn('Failed to copy code:', err);
                this.innerHTML = '❌ Failed';
                setTimeout(() => {
                    this.innerHTML = '📋 Copy';
                }, 2000);
            }
        });

        codeBlock.appendChild(copyButton);
    }

    /**
     * Add language label to code block
     */
    function addLanguageLabel(codeBlock, language) {
        const label = document.createElement('div');
        label.className = 'code-language-label';
        label.textContent = language.toUpperCase();
        label.style.cssText = `
            position: absolute;
            top: 8px;
            left: 8px;
            background: var(--studiorum-gold);
            color: var(--studiorum-shadow);
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
        `;

        codeBlock.appendChild(label);
    }

    // Line numbers function removed - were causing alignment issues

    /* =========================================================================
       SCROLL EFFECTS
       ========================================================================= */

    /**
     * Setup scroll-based effects
     */
    function setupScrollEffects() {
        if (prefersReducedMotion) return;

        // Add scroll-to-top button
        addScrollToTopButton();

        // Note: Removed fade-in animations to fix header disappearing issues
    }

    /**
     * Add scroll to top button
     */
    function addScrollToTopButton() {
        const button = document.createElement('button');
        button.id = 'scroll-to-top';
        button.innerHTML = '↑';
        button.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: var(--studiorum-deep-purple);
            color: var(--studiorum-gold);
            border: 2px solid var(--studiorum-gold);
            font-size: 20px;
            cursor: pointer;
            opacity: 0;
            transform: translateY(100px);
            transition: all 0.3s ease;
            z-index: 1000;
        `;

        button.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });

        // Show/hide based on scroll position
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) {
                button.style.opacity = '1';
                button.style.transform = 'translateY(0)';
            } else {
                button.style.opacity = '0';
                button.style.transform = 'translateY(100px)';
            }
        });

        document.body.appendChild(button);
    }

    /**
     * Setup fade-in animations for elements as they enter viewport
     * DISABLED: Was causing headers to disappear/reappear continuously
     */
    function setupFadeInAnimations() {
        // Commented out - was causing header disappearing issues
        /*
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, observerOptions);

        // Observe elements that should fade in
        const fadeElements = document.querySelectorAll('.feature-cards > *, h2, h3, .admonition');
        fadeElements.forEach(el => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            observer.observe(el);
        });
        */
    }

    /* =========================================================================
       ANIMATION OBSERVER
       ========================================================================= */

    /**
     * Setup intersection observer for animations
     * DISABLED: Was causing header disappearing issues
     */
    function setupAnimationObserver() {
        // Commented out - was causing animation issues
        /*
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate');
                }
            });
        });

        // Observe elements that should animate
        document.querySelectorAll('.feature-cards > *, .hero-banner').forEach(el => {
            observer.observe(el);
        });
        */
    }

    /* =========================================================================
       KEYBOARD NAVIGATION
       ========================================================================= */

    /**
     * Setup keyboard navigation enhancements
     */
    function setupKeyboardNavigation() {
        // Skip link functionality
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.textContent = 'Skip to main content';
        skipLink.className = 'sr-only';
        skipLink.style.cssText = `
            position: absolute;
            top: -40px;
            left: 6px;
            background: var(--studiorum-deep-purple);
            color: var(--studiorum-gold);
            padding: 8px;
            text-decoration: none;
            border-radius: 4px;
            z-index: 1001;
            transition: top 0.3s;
        `;

        skipLink.addEventListener('focus', function() {
            this.style.top = '6px';
        });

        skipLink.addEventListener('blur', function() {
            this.style.top = '-40px';
        });

        document.body.insertBefore(skipLink, document.body.firstChild);

        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            // Alt + H = Home
            if (e.altKey && e.key === 'h') {
                e.preventDefault();
                window.location.href = '/';
            }

            // Alt + S = Search (if search exists)
            if (e.altKey && e.key === 's') {
                e.preventDefault();
                const searchInput = document.querySelector('input[type="search"]');
                if (searchInput) {
                    searchInput.focus();
                }
            }
        });
    }

    /* =========================================================================
       PARALLAX EFFECTS
       ========================================================================= */

    /**
     * Setup subtle parallax effects
     */
    function setupParallaxEffects() {
        const hero = document.querySelector('.hero-banner');
        if (!hero) return;

        window.addEventListener('scroll', () => {
            const scrolled = window.pageYOffset;
            const rate = scrolled * -0.5;

            if (hero.style.transform !== undefined) {
                hero.style.transform = `translate3d(0, ${rate}px, 0)`;
            }
        });
    }

    /* =========================================================================
       INITIALIZATION
       ========================================================================= */

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeTheme);
    } else {
        initializeTheme();
    }

    // Re-initialize on dynamic content changes
    const contentObserver = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Debounce re-initialization
                clearTimeout(window.themeReinitTimeout);
                window.themeReinitTimeout = setTimeout(initializeTheme, 100);
            }
        });
    });

    contentObserver.observe(document.body, {
        childList: true,
        subtree: true
    });

})();
