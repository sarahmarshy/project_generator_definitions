import os

from jinja2 import Template, FileSystemLoader
from jinja2.environment import Environment
import yaml

class MissingInfo(Exception):
    def __init__(self, device, key_error, url):
        Exception.__init__(self)
        self.message = "{0} missing: {1} find at {2}".format(device, key_error, url)

class PackToDict(dict):

    def __init__(self, info, part):
        temp = self.format_info(info, part)
        self.update(self.fill_template(temp))

    def __getitem__(self, key):
        val = dict.__getitem__(self, key)
        return val

    def __setitem__(self, key, val):
        dict.__setitem__(self, key, val)

    def update(self, *args, **kwargs):
        for k, v in dict(*args, **kwargs).iteritems():
            self[k] = v

    def fill_template(self, temp_dict):
        currdir = os.path.dirname(__file__)
        utils = os.path.join(currdir, 'text_utils')
        template_file = os.path.join(utils,'mcu_template.tmpl')
        temp_file = os.path.join(utils, 'temp.yaml')

        env = Environment()
        env.loader = FileSystemLoader(utils)
        # TODO: undefined=StrictUndefined - this needs fixes in templates
        template = env.get_template('mcu_template.tmpl')
        target_text = template.render(temp_dict)

        open(temp_file, "w").write(target_text)
        ret = {}
        with open(temp_file, 'r+') as f:
            ret = yaml.load(f)
        os.remove(temp_file)
        return ret

    def format_info(self, info, part):
        info_dict = info
        try:
            info_dict['cpu_string']=PackToDict.format_cpu(info['memory'],info['processor'],info['core'])
            info_dict['pack_file'] = info_dict['pack_file'].split("/")[-1]
            info_dict['compile']['define'] = info_dict['compile'].get('define',part)
            info_dict['compile']['header'] = PackToDict.format_reg_file(part, info_dict['compile']['header'])
            info_dict['debug'] = info_dict.get('debug','')
            info_dict['debug'] = PackToDict.format_debug(part, info_dict['debug'])
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

        if 'IROM2' in memory:
            rom = 'IROM2({0},{1})'
            start, size = get_bounds('IROM2')
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