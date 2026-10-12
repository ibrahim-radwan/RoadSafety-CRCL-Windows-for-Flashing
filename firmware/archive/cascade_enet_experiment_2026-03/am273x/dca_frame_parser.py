#!/usr/bin/env python3
"""
DCA1000 Frame-by-Frame Parser for AM273x Cascade TDM MIMO.

Reads a raw .bin capture from the DCA1000EVM (LVDS stream) and splits it
into individual per-frame, per-device binary files.

LVDS stream layout (interleaved by chirp line):
    The CBUFF SW session is configured with two user buffers:
      - userBuffer0 = CSIA data (device 0 / master AWR2243)
      - userBuffer1 = CSIB data (device 1 / slave AWR2243)
    Each CBUFF transfer sends one chirp line from each device back-to-back.

Per chirp line per device:
    256 ADC samples * 4 RX * 4 bytes (complex int16 I+Q) = 4096 bytes

Per LVDS transfer (one chirp line, both devices):
    4096 (dev0) + 4096 (dev1) = 8192 bytes

Per frame:
    384 chirp lines * 8192 = 3,145,728 bytes

Usage:
    python dca_frame_parser.py <input.bin> [--out ./frames] [--numpy]

Output:
    frames/frame_0000_dev0.bin
    frames/frame_0000_dev1.bin
    frames/frame_0001_dev0.bin
    ...
"""

import argparse
import os
import struct
import sys


def parse_args():
    p = argparse.ArgumentParser(
        description='Parse DCA1000 cascade capture into per-frame files')
    p.add_argument('input', help='Raw .bin file from DCA1000 capture')
    p.add_argument('--out', default='./frames',
                   help='Output directory (default: ./frames)')
    p.add_argument('--numpy', action='store_true',
                   help='Also save as .npy (requires numpy)')
    p.add_argument('--num-samples', type=int, default=256,
                   help='ADC samples per chirp (default: 256)')
    p.add_argument('--num-rx', type=int, default=4,
                   help='RX channels per device (default: 4)')
    p.add_argument('--num-chirps', type=int, default=6,
                   help='Chirps per frame (default: 6 for TDM MIMO)')
    p.add_argument('--num-loops', type=int, default=64,
                   help='Loops per frame (default: 64)')
    p.add_argument('--num-devices', type=int, default=2,
                   help='Number of cascade devices (default: 2)')
    p.add_argument('--bytes-per-sample', type=int, default=4,
                   help='Bytes per ADC sample, complex (default: 4)')
    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)

    line_bytes = args.num_samples * args.bytes_per_sample * args.num_rx
    chirp_lines_per_frame = args.num_chirps * args.num_loops
    frame_bytes_per_dev = chirp_lines_per_frame * line_bytes
    lvds_transfer_bytes = line_bytes * args.num_devices
    frame_bytes_total = chirp_lines_per_frame * lvds_transfer_bytes

    file_size = os.path.getsize(args.input)
    num_frames = file_size // frame_bytes_total
    remainder = file_size % frame_bytes_total

    print(f'Input file      : {args.input}')
    print(f'File size       : {file_size:,} bytes')
    print(f'Line bytes/dev  : {line_bytes}')
    print(f'Chirp lines/frm : {chirp_lines_per_frame}')
    print(f'Frame bytes     : {frame_bytes_total:,} (both devices)')
    print(f'Complete frames : {num_frames}')
    if remainder:
        print(f'Remainder bytes : {remainder:,} (partial frame, skipped)')
    print()

    with open(args.input, 'rb') as f:
        for frame_idx in range(num_frames):
            dev_data = [bytearray() for _ in range(args.num_devices)]

            for _ in range(chirp_lines_per_frame):
                for d in range(args.num_devices):
                    chunk = f.read(line_bytes)
                    if len(chunk) < line_bytes:
                        print(f'Unexpected EOF at frame {frame_idx}')
                        return
                    dev_data[d].extend(chunk)

            for d in range(args.num_devices):
                fname = os.path.join(
                    args.out, f'frame_{frame_idx:04d}_dev{d}.bin')
                with open(fname, 'wb') as out:
                    out.write(dev_data[d])

                if args.numpy:
                    try:
                        import numpy as np
                        arr = np.frombuffer(dev_data[d], dtype=np.int16)
                        arr = arr.reshape(
                            chirp_lines_per_frame, args.num_rx,
                            args.num_samples, 2)
                        np.save(fname.replace('.bin', '.npy'), arr)
                    except ImportError:
                        pass

            print(f'  Frame {frame_idx:4d} saved  '
                  f'({frame_bytes_per_dev:,} B x {args.num_devices} devices)')

    print(f'\nDone. {num_frames} frames saved to {args.out}/')


if __name__ == '__main__':
    main()
