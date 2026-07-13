function applyTheme(theme) {
    const htmlNode = document.documentElement;
    htmlNode.setAttribute('data-theme', theme);
    localStorage.setItem('synapse-theme', theme);
    
    const themeBtn = document.getElementById('themeBtn');
    if(themeBtn) {
        if(theme === 'dark') {
            if(typeof lucide !== 'undefined') {
                themeBtn.innerHTML = '<i data-lucide="moon" id="themeIcon"></i>';
                lucide.createIcons();
            } else {
                themeBtn.innerHTML = '<i class="fas fa-moon" id="themeIcon"></i>';
            }
        } else {
            if(typeof lucide !== 'undefined') {
                themeBtn.innerHTML = '<i data-lucide="sun" id="themeIcon"></i>';
                lucide.createIcons();
            } else {
                themeBtn.innerHTML = '<i class="fas fa-sun" id="themeIcon"></i>';
            }
        }
    }

    if (typeof Chart !== 'undefined') {
        const rootStyle = getComputedStyle(document.body);
        const textColor = rootStyle.getPropertyValue('--text-primary').trim();
        const gridColor = rootStyle.getPropertyValue('--border-subtle').trim();
        const chartColors = [
            rootStyle.getPropertyValue('--chart-1').trim(),
            rootStyle.getPropertyValue('--chart-2').trim(),
            rootStyle.getPropertyValue('--chart-3').trim()
        ];
        
        Object.values(Chart.instances).forEach(chart => {
            if(chart.options.scales) {
                if(chart.options.scales.x) {
                    if (chart.options.scales.x.ticks) chart.options.scales.x.ticks.color = textColor;
                    if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = gridColor;
                }
                if(chart.options.scales.y) {
                    if (chart.options.scales.y.ticks) chart.options.scales.y.ticks.color = textColor;
                    if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = gridColor;
                }
            }
            if(chart.options.plugins && chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                chart.options.plugins.legend.labels.color = textColor;
            }
            
            if(chart.data && chart.data.datasets) {
                chart.data.datasets.forEach((dataset, index) => {
                    const color = chartColors[index % chartColors.length];
                    // Update only if it's a solid color (ignore gradient backgrounds for now)
                    if (dataset.backgroundColor && typeof dataset.backgroundColor === 'string' && dataset.backgroundColor.includes('rgba')) {
                        dataset.backgroundColor = color;
                    }
                    if (dataset.borderColor && typeof dataset.borderColor === 'string') {
                        dataset.borderColor = color;
                    }
                });
            }
            
            chart.update('none');
        });
    }
}

function toggleTheme() {
    const htmlNode = document.documentElement;
    
    // Add universal transition class to synchronize element repaints
    htmlNode.classList.add('theme-transition');
    
    const currentTheme = htmlNode.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(newTheme);
    
    // Remove transition class after 300ms (matches CSS duration)
    setTimeout(() => {
        htmlNode.classList.remove('theme-transition');
    }, 300);
}

// Auto-initialize theme on load
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('synapse-theme') || 'dark';
    applyTheme(savedTheme);
});
