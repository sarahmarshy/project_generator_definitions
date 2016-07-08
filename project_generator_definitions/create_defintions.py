import os
import sys
import json
import logging
import requests
import shutil

import yaml
import bs4

from ArmPackManager import Cache

currdir = os.path.dirname(__file__)
text_utils = os.path.join(currdir, 'text_utils')



class MCUdef(dict):
    def __init__(self, info):
        for k,v in info.items():
            if type(v) is not dict:
                info[k] = str(v)
        self.__dict = {'mcu':
                 {'core': [info['core'].lower()],
                  'vendor': [info['vendor']],
                  'name': [info['device'].lower()]},
             'tool_specific': {'uvision':
                                   {'TargetOption': {'SFDFile': [info['debug']],
                                                     'Vendor': [info['vendor']],
                                                     'DeviceId': [],
                                                     'Device': [info['device']],
                                                     'Cpu': [info['cpu_string']]
                                                     }
                                    },
                               'uvision5':
                                   {'TargetOption': {'SFDFile': [info['debug']],
                                                     'Vendor': [info['vendor']],
                                                     'DeviceId': [],
                                                     'Device': [info['device']],
                                                     'Cpu': [info['cpu_string']],
                                                     'PackID' :[info['pack_file']],
                                                     'RegisterFile':[info['compile']['header']]
                                                     }
                                    }
                               }
             }

    @property
    def mcu_info(self):
        return self.__dict


class MissingInfo(Exception):
    def __init__(self, device, key_error, url):
        Exception.__init__(self)
        self.message = "{0} missing: {1} find at {2}".format(device, key_error, url)

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
                info = self.format_info(key)
                vendor = info['vendor']
                #check if the vendor is an ARM partner
                if not any(v.lower() in vendor.lower() or vendor.lower() in v.lower()
                           for v in self.partner_list):
                    continue #skip making a yaml if they aren't
                self.make_yaml(info, key)
            except MissingInfo, e:
                print e.message

    def make_yaml(self, data, output):
        dest_path = os.path.join(currdir, "mcu", data['vendor'].lower())
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        output = os.path.join(dest_path, output.split("/")[0].lower()+'.yaml')

        mcu_def = MCUdef(data)
        mcu_info = mcu_def.mcu_info

        if os.path.exists(output):
            with open(output, 'rt') as f:
                old_yaml = yaml.load(f)
                mcu_info.update(old_yaml)

        open(output, "w").write(yaml.dump(mcu_def.mcu_info,default_flow_style=False))

    def format_info(self, part):
        info = self.cache.index[part]
        info_dict = info
        try:
            info_dict['cpu_string']=PackScrape.format_cpu(info['memory'],info['processor'],info['core'])
            info_dict['pack_file'] = info_dict['pack_file'].split("/")[-1]
            info_dict['compile']['define'] = info_dict['compile'].get('define',part)
            info_dict['compile']['header'] = PackScrape.format_reg_file(part, info_dict['compile']['header'])
            info_dict['debug'] = info_dict.get('debug','')
            info_dict['debug'] = PackScrape.format_debug(part, info_dict['debug'])
            info_dict['vendor'] = info_dict['vendor'].split(":")[0]
        except KeyError, e:
            raise MissingInfo(part, str(e), info['pdsc_file'])
        info_dict["device"] = part
        return info_dict

    @staticmethod
    def format_cpu(memory=None, processor=None, core=None):
        cpu = []

        def get_bounds(key):
            return memory[key]['start'], memory[key]['size']

        if 'IROM' in memory:
            rom = 'IROM({0},{1})'
            start,size= get_bounds('IROM')
            cpu.append(rom.format(start,size))

        if 'IROM1' in memory:
            rom = 'IROM({0},{1})'
            start, size = get_bounds('IROM1')
            cpu.append(rom.format(start, size))

        if 'IRAM1' in memory:
            ram = 'IRAM({0},{1})'
            start, size = get_bounds('IRAM1')
            cpu.append(ram.format(start, size))

        if 'IRAM2' in memory:
            ram = 'IRAM2({0},{1})'
            start, size = get_bounds('IRAM2')
            cpu.append(ram.format(start, size))

        cputype = 'CPUTYPE(\"{}\")'
        cpu.append(cputype.format(core))

        if 'fpu' in processor and processor['fpu'] != '0' and processor['fpu'] != "NO_FPU":
            cpu.append("FPU2")

        if 'clock' in processor:
            clock = 'CLOCK({})'
            cpu.append(clock.format(processor['clock']))

        if 'endianness' in processor and processor['endianness'] == "Little-endian":
            cpu.append("ELITTLE")

        return " ".join(cpu)

    @staticmethod
    def format_debug(device_name=None, debug_file=None):
        if debug_file == '': return ''
        sfd = "$$Device:{0}${1}"
        return sfd.format(device_name, debug_file)

    @staticmethod
    def format_reg_file(device_name, include_file):
        reg_file = "$$Device:{0}${1}"
        return reg_file.format(device_name, include_file)

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


