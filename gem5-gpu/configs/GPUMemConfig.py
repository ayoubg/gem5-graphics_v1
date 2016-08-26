# Copyright (c) 2013 Mark D. Hill and David A. Wood
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Authors: Jason Power, Joel Hestness

import math
import m5
import inspect
from m5.objects import *

def addMemCtrlOptions(parser):
    parser.add_option("--mem_ctl_latency", type="int", default=-1, help="Memory controller latency in cycles")
    parser.add_option("--mem_freq", type="string", default="400MHz", help="Memory controller frequency")
    parser.add_option("--membus_busy_cycles", type="int", default=-1, help="Memory bus busy cycles per data transfer")
    parser.add_option("--membank_busy_time", type="string", default=None, help="Memory bank busy time in ns (CL+tRP+tRCD+CAS)")
    parser.add_option("--mem_tFaw", type="int", default=0, help="Memory tFaw cycles")
    parser.add_option("--mem_refresh_period", type="int", default=0, help="Memory refresh period")

def setMemoryControlOptions(system, options):
    from m5.params import Latency

    cpu_mem_ctl_clk = SrcClockDomain(clock = options.mem_freq,
                                     voltage_domain = system.voltage_domain)

    # Setup appropriate address mappings:
    low_dir_bit = int(math.log(options.cacheline_size, 2))
    dir_bits = int(math.log(options.num_dirs, 2))
    # Add 1 so that 2 consecutive cache lines are in the same bank
    low_bank_bit = low_dir_bit + dir_bits + 1

    for i in xrange(options.num_dirs):
        cntrl = eval("system.ruby.dir_cntrl%d" % i)
        if options.mem_freq:
            cntrl.memBuffer.clk_domain = cpu_mem_ctl_clk
        if options.mem_ctl_latency >= 0:
            cntrl.memBuffer.mem_ctl_latency = options.mem_ctl_latency
        if options.membus_busy_cycles > 0:
            cntrl.memBuffer.basic_bus_busy_time = options.membus_busy_cycles
        if options.membank_busy_time:
            mem_cycle_seconds = float(cntrl.memBuffer.clk_domain.clock.period)
            bank_latency_seconds = Latency(options.membank_busy_time)
            cntrl.memBuffer.bank_busy_time = long(bank_latency_seconds.period / mem_cycle_seconds)
        cntrl.memBuffer.tFaw = options.mem_tFaw
        cntrl.memBuffer.refresh_period = options.mem_refresh_period
        cntrl.memBuffer.bank_bit_0 = low_bank_bit
        bank_bits = int(math.log(cntrl.memBuffer.banks_per_rank, 2))
        cntrl.memBuffer.rank_bit_0 = low_bank_bit + bank_bits
        rank_bits = int(math.log(cntrl.memBuffer.ranks_per_dimm, 2))
        cntrl.memBuffer.dimm_bit_0 = low_bank_bit + bank_bits + rank_bits

    dev_dir_bits = 0
    if options.num_dev_dirs > 0:
        dev_dir_bits = int(math.log(options.num_dev_dirs, 2))
    # Add 1 so that 2 consecutive cache lines are in the same bank
    low_bank_bit = low_dir_bit + dev_dir_bits + 1

    if options.split:
        for i in xrange(options.num_dev_dirs):
            cntrl = eval("system.ruby.dev_dir_cntrl%d" % i)
            if options.gpu_mem_freq:
                gpu_mem_ctl_clk = SrcClockDomain(clock = options.gpu_mem_freq,
                                         voltage_domain = system.voltage_domain)
                cntrl.memBuffer.clk_domain = gpu_mem_ctl_clk
            else:
                cntrl.memBuffer.clk_domain = cpu_mem_ctl_clk
            if options.gpu_mem_ctl_latency >= 0:
                cntrl.memBuffer.mem_ctl_latency = options.gpu_mem_ctl_latency
            if options.gpu_membus_busy_cycles > 0:
                cntrl.memBuffer.basic_bus_busy_time = options.gpu_membus_busy_cycles
            if options.gpu_membank_busy_time:
                mem_cycle_seconds = float(cntrl.memBuffer.clk_domain.clock.period)
                bank_latency_seconds = Latency(options.gpu_membank_busy_time)
                cntrl.memBuffer.bank_busy_time = long(bank_latency_seconds.period / mem_cycle_seconds)

            cntrl.memBuffer.bank_bit_0 = low_bank_bit
            bank_bits = int(math.log(cntrl.memBuffer.banks_per_rank, 2))
            cntrl.memBuffer.rank_bit_0 = low_bank_bit + bank_bits
            rank_bits = int(math.log(cntrl.memBuffer.ranks_per_dimm, 2))
            cntrl.memBuffer.dimm_bit_0 = low_bank_bit + bank_bits + rank_bits


#this one uses the simple DRAM model for ruby
def setDRAMMemoryControlOptions(system, options):
   print "Using Ruby DRAM models"
   ctrl_found = False;
   for name, cls in inspect.getmembers(m5.objects):
      if(options.mem_type == name):
         assert(issubclass(cls, m5.objects.MemoryControl) and not(cls.abstract))
         ruby_ctrl = cls
         ctrl_found = True
         break;
   assert (ctrl_found, "Undefined mem-type!")
   nbr_mem_ctrls = options.num_dirs

   import math
   from m5.util import fatal
   intlv_bits = int(math.log(nbr_mem_ctrls, 2))
   if 2 ** intlv_bits != nbr_mem_ctrls:
      fatal("Number of memory channels must be a power of 2")

   # The default behaviour is to interleave on cache line granularity
   cache_line_bit = int(math.log(system.cache_line_size.value, 2)) - 1
   intlv_low_bit = cache_line_bit
   tCK = Latency(cls.tCK)
   cpu_mem_ctl_clk = SrcClockDomain(clock = tCK.frequency,
                                  voltage_domain = system.voltage_domain)

   for r in system.mem_ranges:
      print "Ruby mem range: start:", r.start, ", size:", r.size()
      for i in xrange(options.num_dirs):
         cntrl = eval("system.ruby.dir_cntrl%d" % i)
         cntrl.memBuffer = cls(
                    clk_domain = cpu_mem_ctl_clk,
                    version = i,
                    ruby_system = system.ruby)
         cntrl.memBuffer.channels = nbr_mem_ctrls
         # If the channel bits are appearing after the column
         # bits, we need to add the appropriate number of bits
         # for the row buffer size
         if cntrl.memBuffer.addr_mapping.value == 'RoRaBaChCo':
            # This computation only really needs to happen
            # once, but as we rely on having an instance we
            # end up having to repeat it for each and every one
            rowbuffer_size = cntrl.memBuffer.device_rowbuffer_size.value * cntrl.memBuffer.devices_per_rank.value
            intlv_low_bit = int(math.log(rowbuffer_size, 2)) - 1
         # We got all we need to configure the appropriate address
         # range
         cntrl.memBuffer.range = m5.objects.AddrRange(r.start, size = r.size(),
                                             intlvHighBit = \
                                             intlv_low_bit + intlv_bits,
                                             intlvBits = intlv_bits,
                                             intlvMatch = i)
