/* Plausible Analytics with 404 Error Page Tracking for Studiorum */

// Initialize Plausible function properly
(function() {
    window.plausible = window.plausible || function() { 
        (window.plausible.q = window.plausible.q || []).push(arguments) 
    };
    
    // Load the Plausible script with proper attributes
    var script = document.createElement('script');
    script.defer = true;
    script.setAttribute('data-domain', 'studiorum.dev');
    script.src = 'https://plausible.io/js/script.js';
    document.head.appendChild(script);
})();