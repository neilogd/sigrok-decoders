##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2018 Neil Forbes-Richardson <neilo@neilo.gd>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

import sigrokdecode as srd
from collections import namedtuple

Data = namedtuple('Data', ['ss', 'es', 'val'])

Bit = namedtuple('Bit', 'val ss es')

class Ann:
    BIT, OUTPUT, MANTISSA, EXPONENT = range(4)

class Decoder(srd.Decoder):
    api_version = 3
    id = 'ym3014'
    name = 'YM3014'
    longname = 'Yamaha YM3014 DAC'
    desc = 'Serial Input Floating D/A Converter'
    license = 'gplv2+'
    inputs = ['serial']
    outputs = ['audio']
    channels = (
        {'id': 'clk', 'name': 'CLK', 'desc': 'Clock'},
        {'id': 'sd', 'name': 'SD', 'desc': 'Serial Data'},
        {'id': 'load', 'name': 'LOAD', 'desc': 'Load'},
    )

    annotations = (
        ('bit', 'Bit'),
        ('output', 'Output'),
        ('mantissa', 'Mantissa'),
        ('exponent', 'Exponent'),
    )

    annotation_rows = (
        ('bits', 'Bits', (0,)),
        ('output', 'Output', (1,)),
        ('data', 'Data', (2,3,)),
    )

    binary = (
        ('raw-output', 'Raw Output'),
        ('nrm-output', 'Normalized Output'),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.bits = []
        self.last_load = 0
        self.bit_count = 0
        self.samplenum = 0

    def metadata(self, key, value):
        pass

    def start(self):
        self.out_python = self.register(srd.OUTPUT_PYTHON)
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_binary = self.register(srd.OUTPUT_BINARY)

    def putb(self, bit, ann_idx):
        b = self.bits[bit]
        self.put(b.ss, b.es, self.out_ann, [ann_idx, [str(b.val)]])

    def handle_bits(self, sd, load):
        self.bits.append(Bit(sd, self.samplenum, self.samplenum))        

        if len(self.bits) > 12:
            # Load data into DAC
            if self.last_load == 1 and load == 0:
                self.put(self.bits[10].ss, self.bits[12].es, self.out_ann, [Ann.EXPONENT, ['Exponent']])
                self.put(self.bits[0].ss, self.bits[9].es, self.out_ann, [Ann.MANTISSA, ['Mantissa']])

                # Calculate Vout
                mantissa = -1.0
                mantissa += self.bits[0].val;
                mantissa += self.bits[1].val * 2.0 ** -1.0;
                mantissa += self.bits[2].val * 2.0 ** -2.0;
                mantissa += self.bits[3].val * 2.0 ** -3.0;
                mantissa += self.bits[4].val * 2.0 ** -4.0;
                mantissa += self.bits[5].val * 2.0 ** -5.0;
                mantissa += self.bits[6].val * 2.0 ** -6.0;
                mantissa += self.bits[7].val * 2.0 ** -7.0;
                mantissa += self.bits[8].val * 2.0 ** -8.0;
                mantissa += self.bits[9].val * 2.0 ** -9.0;
                mantissa += 2.0 ** -10.0;

                exponent = 0.0
                exponent += self.bits[10].val
                exponent += self.bits[11].val * 2.0 ** 1
                exponent += self.bits[12].val * 2.0 ** 2

                vin = 5.0
                vout = (vin / 2.0) + (vin / 4.0) * (mantissa * 2.0 ** -10) *  (2.0 ** -exponent)
                normalized = int(((vout - (vin / 4.0)) / (vin / 2.0)) * 65535)
                self.put(self.bits[0].ss, self.bits[12].es, self.out_ann, [Ann.OUTPUT, 
                    ['Vin: %f, Vout: %f, 16-bit: %u' % (vin, vout, normalized)]])


                self.bit_count = 0

            # It's a shift register, so shift out.
            if len(self.bits) > 13:
                self.bits.pop(0)

            self.putb(12, Ann.BIT)

            self.bit_count = self.bit_count + 1

            self.last_load = load

    def decode(self):
        while True:
            # Sample data bits on rising clock edge.
            clk, sd, load = self.wait({0: 'r'})
            self.handle_bits(sd, load)



