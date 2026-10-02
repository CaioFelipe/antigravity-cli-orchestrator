import re

with open(r'C:\Users\aluno\AppData\Local\Programs\antigravity\resources\app.asar', 'rb') as f:
    data = f.read()

matches = re.findall(rb'[a-zA-Z0-9_\.]*relaunch[a-zA-Z0-9_\.]*', data)
for m in sorted(set(matches)):
    print(m.decode(errors='ignore'))

matches2 = re.findall(rb'[a-zA-Z0-9_\.]*restart[a-zA-Z0-9_\.]*', data)
for m in sorted(set(matches2)):
    if 'ls' in m.decode(errors='ignore').lower() or 'server' in m.decode(errors='ignore').lower():
        print(m.decode(errors='ignore'))
