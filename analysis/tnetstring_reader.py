import sys
from collections import Counter
def parse(b, i):
    c = b.index(b":", i); n = int(b[i:c]); d = b[c+1:c+1+n]; t = b[c+1+n:c+2+n]; j = c+2+n
    if t == b",": return d, j
    if t == b";": return d.decode("utf-8","replace"), j
    if t == b"#": return int(d), j
    if t == b"^": return float(d), j
    if t == b"!": return d == b"true", j
    if t == b"~": return None, j
    if t == b"]":
        out=[]; k=0
        while k < len(d): v,k = parse(d,k); out.append(v)
        return out, j
    if t == b"}":
        out={}; k=0
        while k < len(d): key,k=parse(d,k); v,k=parse(d,k); out[key if isinstance(key,str) else key.decode()]=v
        return out, j
    raise ValueError(t)
def flows(path):
    b=open(path,"rb").read(); i=0
    while i < len(b):
        try: f,i = parse(b,i)
        except Exception as e: print("parse stop at",i,e); return
        yield f
