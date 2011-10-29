# vim: set fileencoding=utf-8 ts=4 sts=4 et:

import re
import os.path

class UploadedFile:
    UPLOAD_PATH = '/var/www/upload/'

    REGEXPS = (
            re.compile(r'(filename)=([a-fA-F0-9]{32}\.pdf)'),
            re.compile(r'(originname)=(.*)'),
            re.compile(r'(duplex)=(1|0)'),
            re.compile(r'(blackwhite)=(1|0)'),
            re.compile(r'(remoteaddr)=([a-fA-F0-9\.:]+)'),
        )

    def __init__(self, nonce):
        if not re.match('\d{6}', nonce):
            raise ValueError('Invalid nonce')
        self.filename = os.path.join(self.UPLOAD_PATH, nonce)
        self.results = {}

    def parse(self):
        self.results = {}
        try:
            fh = open(self.filename, 'r')
        except IOError:
            raise ValueError('File not found')

        for line in fh.readlines():
            for r in UploadedFile.REGEXPS:
                m = r.match(line)
                if m:
                    self.results[m.group(1)] = m.group(2)

        self.results['filename'] = os.path.join(self.UPLOAD_PATH, self.results['filename'])

    def get_price(self):
        try:
            fh = open(self.results['filename'] + '.price', 'r')
            price = fh.read(1024*16)
            return float(price)
        except:
            return None
