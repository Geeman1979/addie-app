import re
with open(r'C:\Users\grove\Desktop\addie-app\routes.py', 'r') as f:
    content = f.read()

content = re.sub(
    r"float\(request\.form\.get\('(\w+)',\s*([^)]+)\)\)",
    r"float(request.form.get('\1') or \2)",
    content
)

with open(r'C:\Users\grove\Desktop\addie-app\routes.py', 'w') as f:
    f.write(content)
print('Fixed all float() patterns')
