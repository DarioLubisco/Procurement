import re
import os
import glob

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    new_text = re.sub(r'rgba\(\s*99,\s*102,\s*241\s*,\s*([0-9.]+)\s*\)', r'rgba(var(--primary-rgb), \1)', text, flags=re.IGNORECASE)
    
    # Let's also fix the #9ca3af hex code which is gray-400 used with the pending gray rgba
    new_text = re.sub(r'#9ca3af', r'var(--text-muted)', new_text, flags=re.IGNORECASE)
    # And the gray rgba
    new_text = re.sub(r'rgba\(\s*107,\s*114,\s*128\s*,\s*([0-9.]+)\s*\)', r'rgba(var(--text-muted-rgb, 107, 114, 128), \1)', new_text, flags=re.IGNORECASE)

    if new_text != text:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_text)
        print(f"Updated: {filepath}")

for file in glob.glob('modulo_*.html'):
    process_file(file)
