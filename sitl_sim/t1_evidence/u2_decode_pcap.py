#!/usr/bin/env python3
"""Decode MAVLink2 frames from tcpdump pcap on lo (EN10MB). Usage: u2_decode_pcap.py in.pcap"""
import struct, sys, re
from collections import Counter

XML = "/home/uav/PX4-Autopilot/src/modules/mavlink/mavlink/message_definitions/v1.0/common.xml"
names = {}
try:
    for m in re.finditer(r'<message\b([^>]*)>', open(XML, encoding='utf-8', errors='ignore').read()):
        attrs = m.group(1)
        nm = re.search(r'name="([^"]+)"', attrs); idm = re.search(r'id="(\d+)"', attrs)
        if nm and idm: names[int(idm.group(1))] = nm.group(1)
except Exception as e:
    print("xml parse fail:", e)

data = open(sys.argv[1], 'rb').read()
if data[:4] == b'\xd4\xc3\xb2\xa1': end = '<'
elif data[:4] == b'\xa1\xb2\xc3\xd4': end = '>'
elif data[:4] == b'\x4d\x3c\xb2\xa1': end = '<'   # nanosecond le
else: end = '>'
off = 24
pkts = 0; per = Counter(); lens = Counter(); seqgaps = Counter(); perlen = {}
first_ts = last_ts = None
while off + 16 <= len(data):
    ts, tus, cap, orig = struct.unpack(end + 'IIII', data[off:off+16]); off += 16
    pkt = data[off:off+cap]; off += cap
    if first_ts is None: first_ts = ts + tus/1e6
    last_ts = ts + tus/1e6
    if len(pkt) < 42: continue
    eth = pkt[:14]
    if eth[12:14] != b'\x08\x00': continue
    ip = pkt[14:]
    if (ip[0] >> 4) != 4: continue
    ihl = (ip[0] & 0xf) * 4
    if ip[9] != 17: continue  # UDP
    udp = ip[ihl:]
    sport, dport, ulen = struct.unpack('!HHH', udp[:6])
    payload = udp[8:ulen-8+8]  # ulen includes 8B header
    if not payload or payload[0] != 0xFD: continue
    ln = payload[1]
    frame = payload[:12+ln+2]
    if len(frame) < 12: continue
    msgid = payload[7] | (payload[8] << 8) | (payload[9] << 16)
    seq = payload[4]
    key = (sport, dport, msgid)
    per[key] += 1; perlen.setdefault(msgid, Counter())[ln] += 1
    pkts += 1
dur = (last_ts - first_ts) if first_ts else 0
print(f"total MAVLink2 frames={pkts} duration={dur:.1f}s")
for (sp, dp, mid), n in sorted(per.items(), key=lambda x: -x[1]):
    rate = n/dur if dur else 0
    print(f"  {sp}->{dp} msgid={mid}({names.get(mid,'?')}) n={n} rate={rate:.1f}/s payload_lens={dict(perlen[mid])}")
