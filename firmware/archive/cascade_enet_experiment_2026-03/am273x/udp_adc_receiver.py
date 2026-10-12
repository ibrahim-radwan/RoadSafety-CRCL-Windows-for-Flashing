#!/usr/bin/env python3
"""
UDP ADC Data Receiver for AM273x Cascade Radar Ethernet Streaming.

Listens on UDP port 5001 for ADC frame data from the cascade EVM,
reassembles frames, and saves them as binary files or NumPy arrays.

Usage:
    python udp_adc_receiver.py [--port 5001] [--out ./captures]

Each frame is saved as:
    frame_NNNN_dev0.bin   (raw ADC data from device 0)
    frame_NNNN_dev1.bin   (raw ADC data from device 1)

Data layout per device per frame:
    Shape: (chirp_lines, num_rx * num_samples * 2)
    where factor of 2 = I and Q (complex int16)
"""

import argparse
import os
import socket
import struct
import sys
import time
from collections import defaultdict

MAGIC = 0xADC12345
HEADER_FMT = '<IIHHHHH'
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 20 bytes


def parse_args():
    p = argparse.ArgumentParser(description='Cascade radar UDP ADC receiver')
    p.add_argument('--port', type=int, default=5001,
                   help='UDP port to listen on (default 5001)')
    p.add_argument('--out', type=str, default='./captures',
                   help='Output directory for captured frames')
    p.add_argument('--max-frames', type=int, default=0,
                   help='Stop after N frames (0 = unlimited)')
    p.add_argument('--numpy', action='store_true',
                   help='Also save as .npy (requires numpy)')
    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 16 * 1024 * 1024)
    sock.bind(('0.0.0.0', args.port))
    print(f'Listening on UDP port {args.port} …')

    # frame_data[frame_num][dev_idx] = {chirp_line_idx: bytes}
    frame_data = defaultdict(lambda: defaultdict(dict))
    frame_meta = {}   # frame_num -> (total_chirp_lines, line_bytes)
    saved_frames = 0

    try:
        while True:
            data, addr = sock.recvfrom(65535)
            if len(data) < HEADER_SIZE:
                continue

            (magic, frame_num, dev_idx, chirp_line,
             num_samples, num_rx, bps, total_lines) = \
                struct.unpack(HEADER_FMT, data[:HEADER_SIZE])

            if magic != MAGIC:
                continue

            payload = data[HEADER_SIZE:]
            line_bytes = num_samples * bps * num_rx

            if len(payload) < line_bytes:
                continue

            frame_data[frame_num][dev_idx][chirp_line] = payload[:line_bytes]
            frame_meta[frame_num] = (total_lines, line_bytes)

            # Check if frame is complete for both devices
            meta = frame_meta[frame_num]
            complete = True
            for d in range(2):
                if len(frame_data[frame_num][d]) < meta[0]:
                    complete = False
                    break

            if complete:
                tl, lb = meta
                for d in range(2):
                    out_buf = bytearray(tl * lb)
                    for idx in range(tl):
                        if idx in frame_data[frame_num][d]:
                            out_buf[idx * lb:(idx + 1) * lb] = \
                                frame_data[frame_num][d][idx]
                    fname = os.path.join(
                        args.out, f'frame_{frame_num:04d}_dev{d}.bin')
                    with open(fname, 'wb') as f:
                        f.write(out_buf)

                    if args.numpy:
                        try:
                            import numpy as np
                            arr = np.frombuffer(out_buf, dtype=np.int16)
                            arr = arr.reshape(tl, num_rx, num_samples, 2)
                            np.save(fname.replace('.bin', '.npy'), arr)
                        except ImportError:
                            pass

                saved_frames += 1
                print(f'Frame {frame_num} saved  '
                      f'({tl} chirp lines × {lb} B × 2 devices)  '
                      f'[{saved_frames} total]')

                del frame_data[frame_num]
                del frame_meta[frame_num]

                if args.max_frames and saved_frames >= args.max_frames:
                    print('Reached max frames – exiting.')
                    break

    except KeyboardInterrupt:
        print(f'\nStopped. {saved_frames} frames saved to {args.out}/')
    finally:
        sock.close()


if __name__ == '__main__':
    main()
