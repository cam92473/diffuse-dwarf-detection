import json

x = [1500,2500]
y = [2000,2000]
width = 3000
height = 4000

data = {'x':x,'y':y,'width':width,'height':height}

name = 'test.json'

with open(name,'w') as f:
    json.dump(data, f)