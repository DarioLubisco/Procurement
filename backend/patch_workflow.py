import json
import os

with open(r'C:\Users\DARIO LUBISCO\.gemini\antigravity\brain\c55f3124-4ecf-4db5-b473-ea40ac04448c\.system_generated\steps\4435\output.txt', 'r', encoding='utf-8') as f:
    data_str = f.read()

# The file has a prefix "1: {"
data_str = data_str[data_str.find('{'):]
workflow_data = json.loads(data_str)['workflow']

for node in workflow_data['nodes']:
    if node['name'] == 'Llamar OpenRouter':
        node['name'] = 'Llamar Hermes Agent'
        node['parameters']['url'] = 'http://10.147.18.204:8080/v1/chat/completions'
        node['parameters']['jsonBody'] = '={\n  "model": "deepseek/deepseek-v4-flash",\n  "messages": {{ JSON.stringify($json.messages) }}\n}'

for src, connections in list(workflow_data['connections'].items()):
    if src == 'Preparar Mensajes':
        for target_list in connections['main']:
            for target in target_list:
                if target['node'] == 'Llamar OpenRouter':
                    target['node'] = 'Llamar Hermes Agent'
    if src == 'Llamar OpenRouter':
        workflow_data['connections']['Llamar Hermes Agent'] = connections
        del workflow_data['connections']['Llamar OpenRouter']

with open(r'c:\source\Synapse\backend\updated_workflow.json', 'w', encoding='utf-8') as f:
    json.dump(workflow_data, f, indent=2)

print("Done")
