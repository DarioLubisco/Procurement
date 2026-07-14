import re

file_path = r'c:\source\Synapse\frontend\js\app_cxp.js'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replacements
content = re.sub(r"color:\s*'#f8fafc'", r"color: getComputedStyle(document.body).getPropertyValue('--text-primary').trim() || '#f8fafc'", content)
content = re.sub(r"ctx\.fillStyle\s*=\s*'#f8fafc'", r"ctx.fillStyle = getComputedStyle(document.body).getPropertyValue('--text-primary').trim() || '#f8fafc'", content)

content = re.sub(r"color:\s*'#94a3b8'", r"color: getComputedStyle(document.body).getPropertyValue('--text-muted').trim() || '#94a3b8'", content)
content = re.sub(r"color:\s*'rgba\(255,\s*255,\s*255,\s*0\.05\)'", r"color: getComputedStyle(document.body).getPropertyValue('--border-subtle').trim() || 'rgba(255, 255, 255, 0.05)'", content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Replaced colors successfully.')
