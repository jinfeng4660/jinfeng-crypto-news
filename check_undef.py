import re
c=open('docs/app.js','r',encoding='utf-8').read()
sec=c[c.index('// Helper: kline index'):]
vars_def=set(re.findall(r'(?:var|let|const)\s+(\w+)\s*=', sec))
print("Variables defined:", sorted(vars_def))
potential=re.findall(r"'\+(\w+)\+'", sec)
common={'esc','fmt','minP','maxP','range','startP','endP','isUp','lineColor','areaColor','changePct','chartMinP','chartMaxP','chartRange','margin','leftPad','topPad','btmPad','chW','chH','plotW','plotH','klineCount','chX','chY'}
undef=[v for v in potential if v not in vars_def and v not in common]
print('Possibly undefined:', undef)
