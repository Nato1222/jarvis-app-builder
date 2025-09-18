import os
import sys
from pprint import pprint

# Ensure project root on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi.testclient import TestClient
from JarvisOne.main import app

client = TestClient(app)

# 1) Search for a very likely file name
resp = client.post('/api/tools/search', json={'query': 'main.py'})
print('SEARCH status:', resp.status_code)
search_results = resp.json()
print('SEARCH results (first 5):', search_results[:5])

# 2) Read a known file
path_to_read = 'JarvisOne/main.py' if any(r.endswith('JarvisOne/main.py') for r in search_results) else (search_results[0] if search_results else 'JarvisOne/main.py')
resp2 = client.post('/api/tools/read', json={'path': path_to_read})
print('READ status:', resp2.status_code)
print('READ preview:', (resp2.json() if resp2.headers.get('content-type','').startswith('application/json') else resp2.text)[:200])
