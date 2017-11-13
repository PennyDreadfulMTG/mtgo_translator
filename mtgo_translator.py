# Execute this script at the root of a mtgjson repository clone from https://github.com/mtgjson/mtgjson
import json
import os
import re

# You can change the target language here
TARGET = 'fr'
TARGET_NAME = 'French'

# find the MTGO path.
def find_mtgo():
    mtgo_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'Apps','2.0','Data')
    for _ in range(0, 2):
        mtgo_dir = os.path.join(mtgo_dir, os.listdir(mtgo_dir)[0])
    versions = [folder for folder in os.listdir(mtgo_dir) if ('mtgo..tion' in folder)]
    if len(versions) > 1:
        #TODO: Work out which is newer, and choose that one.
        mtgo_dir = os.path.join(mtgo_dir, versions[1])
    elif versions:
        mtgo_dir = os.path.join(mtgo_dir, versions[0])
    else:
        print("Could not find MTGO data directory.")
        print("Please run MTGO at least once before using this tool.")
        exit
    return os.path.join(mtgo_dir, 'Data','CardDataSource')

mtgo_dir = find_mtgo()

cardnames_fn_xml = 'CARDNAME_STRING.xml'
oracles_fn_xml = 'REAL_ORACLETEXT_STRING.xml'
flavors_fn_xml = 'FLAVORTEXT_STRING.xml'

cardnames_xml = open(mtgo_dir + os.sep + cardnames_fn_xml, 'rb').read()
oracles_xml = open(mtgo_dir + os.sep + oracles_fn_xml, 'rb').read()
flavors_xml = open(mtgo_dir + os.sep + flavors_fn_xml, 'rb').read()

# making backups
open(mtgo_dir + os.sep + cardnames_fn_xml + '.bak', 'wb').write(cardnames_xml)
open(mtgo_dir + os.sep + oracles_fn_xml + '.bak', 'wb').write(oracles_xml)
open(mtgo_dir + os.sep + flavors_fn_xml + '.bak', 'wb').write(flavors_xml)

local = []
base = []

cards = {}

for fn in os.listdir('json'):
    if not fn.endswith('.json'): continue
    if fn.endswith(TARGET + '.json'):
        local.append(fn)
    elif fn.count('.') == 1:
        base.append(fn)

for fn in base:
    ext = json.load(open('json' + os.sep + fn,'r'))
    for card in ext['cards']:
        name = card['name']

        mid = None

        if 'names' in card and len(card['names']) > 1:
            continue # issue with flip cards

        if 'foreignNames' not in card:
            continue
    
        for foreign in card['foreignNames']:
            if foreign['language'] == TARGET_NAME and 'multiverseid' in foreign:
                local_name = foreign['name']
                mid = foreign['multiverseid']
                break

        if mid is None:
            continue

        if 'text' not in card:
            continue

        oracle = card['text']     

        if mid not in cards:
            cards[mid] = {}

        cards[mid]['name'] = name
        cards[mid]['translated_name'] = local_name
        cards[mid]['oracle_text'] = oracle

        if 'flavor' in card:
            cards[mid]['flavor'] = card['flavor']


for fn in local:
    ext = json.load(open('json' + os.sep + fn,'r'))
    for card in ext['cards']:
        mid = card['multiverseid']

        if mid not in cards:
            continue

        c = cards[mid]
        c['translated_text'] = card['originalText']
        if 'flavor' in card:
            c['translated_flavor'] = card['flavor']

cards_by_name = {}
for mid in cards:
    card = cards[mid]
    if 'name' not in card:
        print(card)
    name = cards[mid]['name']
    cards_by_name[name] = cards[mid]



re_card_name = re.compile(r"\s*<CARDNAME_STRING_ITEM id='(?P<id>.*)'>(?P<text>.*)</CARDNAME_STRING_ITEM>")
re_id = re.compile(r"\s*<(?P<type>.*) id='(?P<id>.*)'/>")

ids_database = {}

for fn in os.listdir(mtgo_dir):
    if not fn.startswith('client_'):
        continue
    lines = open(mtgo_dir + os.sep + fn, 'r').read().split('\n')
    i = 0
    while i < len(lines):
        if '<DigitalObject' in lines[i]:
            cardname_id = None
            oracle_id = None
            flavor_id = None

            j = i+1
            while 'DigitalObject' not in lines[j]:
                m = re_id.match(lines[j])
                if m is not None:
                    typ = m.group('type')
                    id = m.group('id')
                    if typ == 'CARDNAME_STRING':
                        cardname_id = id
                    elif typ == 'REAL_ORACLETEXT_STRING':
                        oracle_id = id
                    elif typ == 'FLAVORTEXT_STRING':
                        flavor_id = id
                j += 1
                if cardname_id is not None:
                    if cardname_id in ids_database:
                        ids = ids_database[cardname_id]
                        if oracle_id is not None:
                            ids['oracle'] = oracle_id
                        if flavor_id is not None:
                            ids['flavor'] = flavor_id
                    else:
                        ids_database[cardname_id] = { 'oracle' : oracle_id, 'flavor' : flavor_id }
            i = j
        i += 1

cardnames_xml = cardnames_xml.decode('latin-1')
card_name_by_mtgo_id = {}

output = '<?xml version="1.0" encoding="UTF-8"?>\n'
for ln in cardnames_xml.split('\n')[1:]:
    m = re_card_name.match(ln)
    if m is None:
        output += ln + '\n'
        continue
    id = m.group('id') 
    name = m.group('text').replace("\\'", "'")

    card_name_by_mtgo_id[id] = name
    if name in cards_by_name and 'translated_name' in cards_by_name[name]:
        card = cards_by_name[name]
        name = card['translated_name']

    name = name.replace("'","\\'")
    output += "<CARDNAME_STRING_ITEM id='%s'>%s</CARDNAME_STRING_ITEM>\n" % (id, name)

open(mtgo_dir + os.sep + cardnames_fn_xml, 'wb').write(output.encode('utf-8', 'replace'))

oracles_xml = oracles_xml.decode('latin-1')

card_id_by_oracle_id = {}
for card_id in ids_database:
    ids = ids_database[card_id]
    if ids['oracle'] is not None:
        card_id_by_oracle_id[ids['oracle']] = card_id

re_oracle_text = re.compile(r"\s*<REAL_ORACLETEXT_STRING_ITEM id='(?P<id>.*)'>(?P<text>.*)</REAL_ORACLETEXT_STRING_ITEM>")

n_oracle_tr = 0
output = '<?xml version="1.0" encoding="UTF-8"?>\n'
for ln in oracles_xml.split('\n')[1:]:
    m = re_oracle_text.match(ln)
    if m is None:
        output += ln + '\n'
        continue
    id = m.group('id') 
    text = m.group('text')
    if id in card_id_by_oracle_id:
        card_id = card_id_by_oracle_id[id]
        name = card_name_by_mtgo_id[card_id]
        if name in cards_by_name:
            card = cards_by_name[name]
            if 'translated_text' in card:
                text = card['translated_text']
                text = text.replace("'","\\'")
                text = text.replace("\n", "\\n")
                text = text.replace("{W/U}", "{;a}")
                text = text.replace("{W/B}", "{;b}")
                text = text.replace("{U/B}", "{;c}")
                text = text.replace("{U/R}", "{;d}")
                text = text.replace("{B/R}", "{;e}")
                text = text.replace("{B/G}", "{;f}")
                text = text.replace("{R/G}", "{;g}")
                text = text.replace("{R/W}", "{;h}")
                text = text.replace("{G/W}", "{;i}")
                text = text.replace("{G/U}", "{;j}")
                text = text.replace("—", "@-")
                text = text.replace("(", "@i(")
                text = text.replace(")", ")@i")
                n_oracle_tr += 1
    output += "<REAL_ORACLETEXT_STRING_ITEM id='%s'>%s</REAL_ORACLETEXT_STRING_ITEM>\n" % (id, text)

print('%d oracle texts translated' % n_oracle_tr)
open(mtgo_dir + os.sep + oracles_fn_xml, 'wb').write(output.encode('utf-8', 'replace'))

flavors_xml = flavors_xml.decode('latin-1')

card_id_by_flavor_id = {}
for card_id in ids_database:
    ids = ids_database[card_id]
    if ids['flavor'] is not None:
        card_id_by_flavor_id[ids['flavor']] = card_id

re_flavor_text = re.compile(r"\s*<FLAVORTEXT_STRING_ITEM id='(?P<id>.*)'>(?P<text>.*)</FLAVORTEXT_STRING_ITEM>")

n_flavor_tr = 0
output = '<?xml version="1.0" encoding="UTF-8"?>\n'
for ln in flavors_xml.split('\n')[1:]:
    m = re_flavor_text.match(ln)
    if m is None:
        output += ln + '\n'
        continue
    id = m.group('id') 
    text = m.group('text')
    if id in card_id_by_flavor_id: # and n_flavor_tr < 1225:
        card_id = card_id_by_flavor_id[id]
        name = card_name_by_mtgo_id[card_id]
        if name in cards_by_name:
            card = cards_by_name[name]
            if 'translated_flavor' in card:
                text = card['translated_flavor']
                text = text.replace("'","\\'")
                text = text.replace("\n", "\\n")
                text = text.replace("—", "@-")
                text = text.replace("« ", "\\\"")
                text = text.replace("<< ", "\\\"")
                text = text.replace(" »", "\\\"")
                text = text.replace(" >>", "\\\"")
                text = '@i' + text + '@i'
                n_flavor_tr += 1
    output += "<FLAVORTEXT_STRING_ITEM id='%s'>%s</FLAVORTEXT_STRING_ITEM>\n" % (id, text)

print('%d flavor texts translated' % n_flavor_tr)
open(mtgo_dir + os.sep + flavors_fn_xml, 'wb').write(output.encode('utf-8', 'replace'))