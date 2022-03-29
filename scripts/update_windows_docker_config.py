import json

FILE = 'C:\\ProgramData\\Docker\\config\\daemon.json'

with open(FILE, encoding='utf-8') as fp:
    conf = json.load(fp)

conf['experimental'] = True

with open(FILE, 'w', encoding='utf-8') as fp:
    json.dump(conf, fp)
