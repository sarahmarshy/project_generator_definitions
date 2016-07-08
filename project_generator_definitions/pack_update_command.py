# Copyright 2015 0xc0170
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .create_defintions import PackScrape

help = 'Use arm-pack-manager to scrape definitions from pack files'


def run(args):
    p = PackScrape(args.cache, args.partners)
    p.dump_files()


def setup(subparser):
    subparser.add_argument(
        '-c', action='store_true', dest='cache', help='Cache pack files')

    subparser.add_argument(
        '-p', action='store_true', dest='partners',
        help='Update partners.json from https://www.mbed.com/en/partners/our-partners/')
