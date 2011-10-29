#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# the following data must be available via environment:
# TEACLIENTHOST TEADATAFILE TEAJOBID TEATITLE
# expects the following two positional arguments:
# PRINTER [for logging purposes]

# depending on OPERATION, we do only pricecalc or real print

import os
import sys
import traceback
import re
import subprocess
import signal
import shutil
import tempfile
# local print library
import printerlib

#configurable stuff
# 0. Enable print (disabling allows testing)
ENABLE_PRINT = True
# 1. PRICE (extra notes on these values see below)
# Note: Unit is Euros
PRICE_PAPER_SHEET = 0.008
PRICE_FUSER_PAGE = 0.002
# these values are per 5% covered page (which is the industry standard)
PRICE_BLACK_PAGE = 0.015
PRICE_COLOR_PAGE = 0.040
# 2. PKPGCOUNTER
PKPGCOUNTER_BIN = '/usr/bin/pkpgcounter'
# resolution used for price calculation; higher means longer processing time
PKPGCOUNTER_RESOLUTION = 144
# 3. MISC
# billing configuration based on billing codes
BILLING_CONF = { 'black_simplex' : { 'color': False, 'duplex': False },
                 'black_duplex'  : { 'color': False, 'duplex': True },
                 'color_simplex' : { 'color': True,  'duplex': False },
                 'color_duplex'  : { 'color': True,  'duplex': True } }
LOGFILE = '/var/log/printer_prices.log'
#end configurable stuff

# Notes on price settings:
# price calculation for black toner usage:
# our cost for black toner is about 140€ for 10500 pages based on 
# 5% toner usage; this means 1.33¢ = 13.3 millicent for a 5% covered page.
# We will use 15 millicent instead, to earn some extra $$$ :)
# price calculation for color toner usage:
# our cost for color toner (same for all colors) is about 190€ for 7000
# pages based on 5% toner usage; this means 2.71¢ = 27.1 millicent
# for a 5% covered page. We will use 40 millicent instead, since I have
# noticed, that the printer uses more toner than the pkpgcounter assumes
# an additional 2 millicent per page for FUSER and TONER_COLLECTOR costs

PKPGCOUNTER_COLOR_REGEX = re.compile(r'^C :\s*(\d*\.\d*)%\s*' \
                                     r'M :\s*(\d*\.\d*)%\s*' \
                                     r'Y :\s*(\d*\.\d*)%\s*' \
                                     r'K :\s*(\d*\.\d*)%\s*$')
PKPGCOUNTER_BLACKWHITE_REGEX = re.compile(r'^B :\s*(\d*\.\d*)%\s*$')
PKPGCOUNTER_BUG_RE = re.compile('^ERROR: Unsupported file format for ' \
                '/var/spool/cups/tmp/tmp.* \(input file ' \
                '/var/spool/cups/tmp/tmp.* is empty !\)$')

def handler(signum, frame):
    raise Exception

def pricecalc(dl, datafile, color_duplex):
    dl.setlogstring("pricecalc")

    sum_cyan = sum_magenta = sum_yellow = sum_black = 0.0
    pages = 0

    if color_duplex['color']:
        bw_color = "color"
        pkpgcounter_colorspace = 'cmyk'
        pkpgcounter_expression = PKPGCOUNTER_COLOR_REGEX
    else:
        bw_color = "black/white"
        pkpgcounter_colorspace = 'bw'
        pkpgcounter_expression = PKPGCOUNTER_BLACKWHITE_REGEX

    os.environ['TMPDIR'] = tempfile.mkdtemp()
    try:
        p = subprocess.Popen([PKPGCOUNTER_BIN, '--colorspace',
                              pkpgcounter_colorspace,
                              '-r%d' % (PKPGCOUNTER_RESOLUTION,), datafile],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pkpgcounter_output = p.communicate()
    except Exception:
        p.terminate()
        shutil.rmtree(os.environ['TMPDIR'])
        sys.exit(-1)
    shutil.rmtree(os.environ['TMPDIR'])
    del os.environ['TMPDIR']
    pkpgcounter_stdout = pkpgcounter_output[0].rstrip()
    for line in pkpgcounter_stdout.split('\n'):
        if line.startswith('%'):
            continue
        m = pkpgcounter_expression.match(line)
        if m:
            if color_duplex['color']:
                sum_cyan += float(m.group(1))
                sum_magenta += float(m.group(2))
                sum_yellow += float(m.group(3))
                sum_black += float(m.group(4))
            else:
                sum_black += float(m.group(1))
            pages += 1

        else:
            dl.logit("Unknown Line (pkpgcounter-output): " + line)
            sys.exit(-1)
    pkpgcounter_stderr = pkpgcounter_output[1].rstrip()
    for line in pkpgcounter_stderr.split('\n'):
        if line != '' and not PKPGCOUNTER_BUG_RE.match(line):
            dl.logit("Stderr pkpgcounter: %s" % (line,))

    # base toner usages on 5% coverage
    black_toner_pages = sum_black/5
    color_toner_pages = (sum_cyan+sum_magenta+sum_yellow)/5


    #calculate number of sheets (depends on simplex/duplex)
    if color_duplex['duplex']:
        #round up on odd pagenumber
        paper_sheets = (pages+1)/2
        duplex_simplex = 'duplex'
    else:
        paper_sheets = pages
        duplex_simplex = 'simplex'
    #prices calculation
    price = 0;
    price += black_toner_pages * PRICE_BLACK_PAGE
    price += color_toner_pages * PRICE_COLOR_PAGE
    price += pages * PRICE_FUSER_PAGE
    price += paper_sheets * PRICE_PAPER_SHEET
    dl.logit("black pages: %.2f, color pages: %.2f, pages (fuser): %d, sheets: %d"  % (black_toner_pages, color_toner_pages, pages, paper_sheets))

    return price

def parse_billinginfo(infile):
    fd = open(infile, 'r')
    # Get Infos from Inputfile
    is_adobe_ps = re.compile(r'^%!PS-Adobe-3.0')
    is_duplex = re.compile(r'^\s*<</Duplex true /Tumble (true|false)\s*>>')
    is_blackwhite = re.compile(r'^\s*<</ProcessColorModel /DeviceGray>>')
    config = { 'color': True,  'duplex': False }
    adobe_ps = False
    for line in fd:
        if (not adobe_ps) and is_adobe_ps.match(line):
            adobe_ps = True
        elif (not config['duplex']) and is_duplex.match(line):
            config['duplex'] = True
        elif config['color'] and is_blackwhite.match(line):
            config['color'] = False
    fd.close()
    if not adobe_ps:
        sys.exit(-1)
    return config

def main():
    signal.signal(signal.SIGTERM, handler)
    if len(sys.argv) < 2:
        sys.exit(-1)
    if sys.argv[1] == 'pricecalc':
        loghandle = open(os.devnull, 'w')
        dl = printerlib.PrinterLib(loghandle, "init")
        billingcode = sys.argv[2]
        datafile = sys.argv[3]
    elif sys.argv[1] == 'print':
        loghandle = open(LOGFILE, 'a')
        dl = printerlib.PrinterLib(loghandle, "init")
        try:
            datafile = os.environ['TEADATAFILE']
            jobid = os.environ['TEAJOBID']
            jobtitle = os.environ['TEATITLE']
            billingcode = os.environ['TEABILLING']
        except KeyError, e:
            dl.logit("Error: required environment variable '%s' is unset" \
                     % (e[0],))
            sys.exit(-1)
    else:
        sys.exit(-1)

    if billingcode == '':
        color_duplex = parse_billinginfo(datafile)
    else:
        try:
            color_duplex = BILLING_CONF[billingcode]
        except KeyError, e:
            dl.logit("Error: Unknown job-billing option: '%s'" % (e[0],))
            sys.exit(-1)

    price = pricecalc(dl, datafile, color_duplex)
    if sys.argv[1] == 'pricecalc':
        if sys.argv[4] == 'file':
            fd = open(sys.argv[5], 'w')
            fd.write('%.2f\n' % (price,))
            fd.close()
        elif sys.argv[4] == 'stdout':
            print '%.2f' % (price,)
    elif sys.argv[1] == 'print':
        try:
            printername = sys.argv[2]
        except IndexError:
            dl.logit("Error: Printer Name missing")
            sys.exit(-1)
        if color_duplex['color']:
            bw_color = 'color'
        else:
            bw_color = 'black/white'
        if color_duplex['duplex']:
            duplex_simplex = 'duplex'
        else:
            duplex_simplex = 'simplex'
       
        dl.logit("Printing jobid %s (%s %s) with title '%s' on printer %s; " \
                 "price is %.2f €" % (jobid, duplex_simplex, bw_color, jobtitle,
                                        printername, price))
        if not ENABLE_PRINT:
            sys.exit(-1)
    del dl
    sys.exit(0)

if __name__ == "__main__":
    main()
