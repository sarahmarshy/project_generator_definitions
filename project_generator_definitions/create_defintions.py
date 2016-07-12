import os
import sys
import json
import logging
import shutil

import yaml
import bs4
import requests

from ArmPackManager import Cache
from pack_to_dict import PackToDict, MissingInfo

currdir = os.path.dirname(__file__)
text_utils = os.path.join(currdir, 'text_utils')

class PackScrape():
    def __init__(self, cache, partners):
        logging.basicConfig(level=logging.INFO)
        self.cache = Cache(True, False)
        if cache:
            #cache pack descriptors if the user has specified -c
            self.cache.cache_descriptors()
        partner_file = os.path.join(text_utils, 'partners.json')
        if partners:
            #scrape mbed.com for a list of our partners
            partners = self.scrape_mbed_partners('https://www.mbed.com/en/partners/our-partners/')
            with open(partner_file, 'w') as out:
                #write it to a json file
                json.dump(partners, out)
        self.partner_list = []
        try:
            with open(partner_file) as infile:
                self.partner_list = json.load(infile)
        except IOError:
            logging.error("Run the command with -p to update partner list")
            sys.exit(0)

    def dump_files(self):
        for key in self.cache.index.keys():
            try:
                info = PackToDict(self.cache.index[key], key)
                vendor = info['mcu']['vendor'][0]
                #check if the vendor is an ARM partner
                if not any(v.lower() in vendor.lower() or vendor.lower() in v.lower()
                           for v in self.partner_list):
                    continue #skip making a yaml if they aren't
                self.make_yaml(info, key)
            except MissingInfo, e:
                print e.message

    def make_yaml(self, data, output):
        dest_path = os.path.join(currdir, "mcu", data['mcu']['vendor'][0].lower())
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        output = os.path.join(dest_path, output.split("/")[0].lower()+'.yaml')

        if os.path.exists(output):
            with open(output, 'rt') as f:
                old_yaml = yaml.load(f)
                data.update(old_yaml)

        open(output, "w").write(yaml.dump(dict(data),default_flow_style=False))

    def scrape_mbed_partners(self, url):
        res = requests.get(url)
        res.raise_for_status()
        soup = bs4.BeautifulSoup(res.text, "html.parser")
        partners = ['arm', 'freescale'] #default partners (Freescale because only listed as NXP on website)
        for section in soup.find_all('h2'):
            header = section.getText()
            if not 'Silicon Partners' in header:
                continue

            cl = section.find_next_siblings()[0]
            for a in cl.select('li > a'):
                partners.append(a.get('title'))
        return partners



