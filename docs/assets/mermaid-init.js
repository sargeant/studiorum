// Mermaid.js v11 initialization for Studiorum Documentation
document.addEventListener('DOMContentLoaded', function() {
    if (typeof mermaid !== 'undefined') {
        console.log('Mermaid version:', mermaid.version || 'Version not available');

        // Simple v11 initialization - let mermaid handle everything
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            fontFamily: '"Libre Baskerville", serif',
            flowchart: {
                htmlLabels: true,
                useMaxWidth: true,
                curve: 'basis'
            },
            sequence: {
                useMaxWidth: true,
                diagramMarginX: 50,
                diagramMarginY: 10
            },
            gantt: {
                useMaxWidth: true,
                leftPadding: 75,
                rightPadding: 20
            },
            journey: {
                useMaxWidth: true
            },
            gitGraph: {
                useMaxWidth: true
            },
            pie: {
                useMaxWidth: true
            },
            quadrantChart: {
                useMaxWidth: true
            },
            xyChart: {
                useMaxWidth: true
            },
            classDiagram: {
                useMaxWidth: true
            },
            stateDiagram: {
                useMaxWidth: true
            }
        });

        // Debug info
        setTimeout(function() {
            const diagrams = document.querySelectorAll('.mermaid');
            console.log('Found', diagrams.length, 'mermaid diagrams');
            diagrams.forEach((el, i) => {
                console.log(`Diagram ${i}:`, el.textContent?.slice(0, 50) + '...');
            });
        }, 1000);
    } else {
        console.error('Mermaid not loaded');
    }
});
