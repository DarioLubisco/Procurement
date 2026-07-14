import re
import os
import glob

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Hex to Var Map
    hex_to_var = {
        r'#10b981': 'var(--success)',
        r'#22c55e': 'var(--success)',
        r'#ef4444': 'var(--danger)',
        r'#b91c1c': 'var(--danger)',
        r'#f59e0b': 'var(--warning)',
        r'#eab308': 'var(--warning)',
        r'#fb923c': 'var(--warning)',
        r'#f97316': 'var(--warning)',
        r'#3b82f6': 'var(--primary-accent)',
        r'#60a5fa': 'var(--primary-hover)',
        r'#8b5cf6': 'var(--accent-neon)',
        r'#a855f7': 'var(--accent-neon)',
        r'#a78bfa': 'var(--accent-neon)',
        r'#c026d3': 'var(--accent-neon)'
    }

    # RGBA to Var RGB Map
    rgba_patterns = [
        (r'rgba\(\s*(?:16,\s*185,\s*129|34,\s*197,\s*94)\s*,\s*([0-9.]+)\s*\)', r'rgba(var(--success-rgb), \1)'),
        (r'rgba\(\s*(?:239,\s*68,\s*68|185,\s*28,\s*28)\s*,\s*([0-9.]+)\s*\)', r'rgba(var(--danger-rgb), \1)'),
        (r'rgba\(\s*(?:245,\s*158,\s*11|234,\s*179,\s*8)\s*,\s*([0-9.]+)\s*\)', r'rgba(var(--warning-rgb), \1)'),
        (r'rgba\(\s*(?:59,\s*130,\s*246|37,\s*99,\s*235|79,\s*70,\s*229)\s*,\s*([0-9.]+)\s*\)', r'rgba(var(--primary-rgb), \1)'),
        (r'rgba\(\s*(?:168,\s*85,\s*247|139,\s*92,\s*246|167,\s*139,\s*250)\s*,\s*([0-9.]+)\s*\)', r'rgba(var(--accent-neon-rgb), \1)')
    ]

    new_text = text
    
    for h, v in hex_to_var.items():
        new_text = re.sub(h, v, new_text, flags=re.IGNORECASE)

    for p, repl in rgba_patterns:
        new_text = re.sub(p, repl, new_text, flags=re.IGNORECASE)

    # Convert glass classes
    new_text = re.sub(r'\bglass-card\b', 'glassmorphism', new_text)
    new_text = re.sub(r'\bglass-panel\b', 'glassmorphism', new_text)

    # Any other specific inline styles that break theme
    new_text = re.sub(r'background:\s*#111827\b', 'background: var(--bg-surface)', new_text)
    new_text = re.sub(r'background-color:\s*#111827\b', 'background-color: var(--bg-surface)', new_text)

    if new_text != text:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print(f"Updated: {filepath}")

# Process HTML files
for file in glob.glob('modulo_*.html'):
    process_file(file)

for file in glob.glob('index.html'):
    process_file(file)

# Process CSS files
for file in glob.glob('css/*.css'):
    process_file(file)

print("Done.")
