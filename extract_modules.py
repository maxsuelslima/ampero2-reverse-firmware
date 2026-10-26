import json
with open('/home/maico/Programming/ampero2/Ampero II/data/flutter_assets/assets/data/algorithm.json') as f:
    data = json.load(f)
for module in data['PluginProperties']['Modules']['Catalog']:
    print(f"{module['Name']} Index={module['Index']} Effects={len(module['Alg'])}")
    for alg in module['Alg']:
        print(f"  Code={alg['Code']} Name={alg['Name']} Classify={alg.get('classify','')} Index={alg['Index']}")