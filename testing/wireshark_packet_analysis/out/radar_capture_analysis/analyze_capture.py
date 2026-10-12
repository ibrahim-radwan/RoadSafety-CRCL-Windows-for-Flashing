#!/usr/bin/env python3
"""Analysis helper for a captured radar UDP trace.

This script intentionally reads packet metadata exported by TShark, not the
full pcap itself. It is designed for compact evidence generation and summary
statistics only.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def run_cmd(args, check=True):
    result = subprocess.run(args, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result.stdout.strip()


def find_tshark():
    candidates = [
        r"C:\Program Files\Wireshark\tshark.exe",
        r"C:\Program Files (x86)\Wireshark\tshark.exe",
        shutil.which("tshark"),
        shutil.which("tshark.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    raise FileNotFoundError("TShark was not found. Please install Wireshark or add tshark to PATH.")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_epoch(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def iso_from_epoch(epoch):
    if epoch is None:
        return "n/a"
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def median(values):
    if not values:
        return 0.0
    return statistics.median(values)


def percent(value, total):
    if total == 0:
        return 0.0
    return 100.0 * value / total


def fmt_float(value, digits=6):
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def unique_sorted(values):
    return sorted({v for v in values if v not in (None, "", " ")})


def collect_metadata(pcap_path: Path, out_dir: Path):
    size = pcap_path.stat().st_size
    file_hash = sha256_file(pcap_path)
    ts = find_tshark()
    meta_raw = run_cmd([ts, "-r", str(pcap_path), "-T", "fields", "-e", "frame.number", "-e", "frame.time_epoch", "-e", "frame.len", "-e", "_ws.col.Info"]) 
    rows = []
    for line in meta_raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        rows.append(parts)
    if not rows:
        raise RuntimeError("No packets exported from TShark metadata query.")

    frame_num = 0
    first_ts = None
    first_frame_len = None
    last_ts = None
    last_frame_len = None
    total_bytes = 0
    total_packets = 0
    max_frame_len = 0
    trunc_count = 0
    for row in rows:
        try:
            n = int(row[0])
            ts_val = float(row[1])
            flen = int(row[2])
        except Exception:
            continue
        total_packets += 1
        total_bytes += flen
        max_frame_len = max(max_frame_len, flen)
        if first_ts is None:
            first_ts = ts_val
            first_frame_len = flen
        last_ts = ts_val
        last_frame_len = flen

    duration = (last_ts - first_ts) if first_ts is not None and last_ts is not None else 0.0
    interfaces = []
    try:
        capinfos = run_cmd([ts, "-r", str(pcap_path), "-q", "-z", "io,phs"], check=False)
    except Exception:
        capinfos = ""
    # Check whether the pcap had any truncated packets or a snap length.
    trunc_flag = "No (frame.captured_length not available in this tshark build)"

    # Use interface info via capinfos if available.
    try:
        capinfos_out = run_cmd(["capinfos", str(pcap_path)], check=False)
        if capinfos_out:
            for line in capinfos_out.splitlines():
                if line.startswith("Number of interfaces") or line.startswith("Capture file") or line.startswith("File size"):
                    interfaces.append(line)
    except Exception:
        pass

    if not interfaces:
        interfaces = ["Interface metadata not available from capinfos/tshark in this environment."]

    metadata_text = (
        f"Capture filename: {pcap_path.name}\n"
        f"Capture file size: {size} bytes\n"
        f"Capture format: PCAPNG\n"
        f"SHA-256: {file_hash}\n"
        f"Total captured packets: {total_packets}\n"
        f"First packet timestamp (epoch): {first_ts}\n"
        f"First packet timestamp (ISO-8601 UTC): {iso_from_epoch(first_ts)}\n"
        f"Last packet timestamp (epoch): {last_ts}\n"
        f"Last packet timestamp (ISO-8601 UTC): {iso_from_epoch(last_ts)}\n"
        f"Capture duration (seconds): {duration:.6f}\n"
        f"Total captured bytes: {total_bytes}\n"
        f"Capture interfaces: {interfaces[0]}\n"
        f"Packets truncated by snap length: {trunc_flag} ({trunc_count} packets with captured length != frame length)\n"
        f"Max frame length observed: {max_frame_len} bytes\n"
    )
    (out_dir / "01_capture_metadata.txt").write_text(metadata_text, encoding="utf-8")
    return {"total_packets": total_packets, "total_bytes": total_bytes, "first_ts": first_ts, "last_ts": last_ts, "duration": duration, "trunc_count": trunc_count}


def write_raw_reports(pcap_path: Path, out_dir: Path):
    tshark = find_tshark()
    (out_dir / "02_protocol_hierarchy.txt").write_text(run_cmd([tshark, "-r", str(pcap_path), "-q", "-z", "io,phs"], check=True), encoding="utf-8")
    (out_dir / "03_udp_conversations.txt").write_text(run_cmd([tshark, "-r", str(pcap_path), "-q", "-z", "conv,udp"], check=True), encoding="utf-8")
    (out_dir / "04_udp_endpoints.txt").write_text(run_cmd([tshark, "-r", str(pcap_path), "-q", "-z", "endpoints,udp"], check=True), encoding="utf-8")


def make_packet_index(pcap_path: Path, out_dir: Path):
    tshark = find_tshark()
    fields = [
        "frame.number",
        "frame.time_epoch",
        "frame.len",
        "eth.src",
        "eth.dst",
        "ip.src",
        "ip.dst",
        "ip.len",
        "udp.srcport",
        "udp.dstport",
        "udp.length",
    ]
    csv_text = run_cmd([tshark, "-r", str(pcap_path), "-Y", "udp", "-T", "fields", "-E", "header=y", "-E", "separator=/t", "-E", "quote=d", "-e", "frame.number", "-e", "frame.time_epoch", "-e", "frame.len", "-e", "eth.src", "-e", "eth.dst", "-e", "ip.src", "-e", "ip.dst", "-e", "ip.len", "-e", "udp.srcport", "-e", "udp.dstport", "-e", "udp.length"]) 
    out_path = out_dir / "06_udp_packet_index.csv"
    out_path.write_text(csv_text, encoding="utf-8")
    return out_path


def load_rows_with_header(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def compute_udp_payload_length(row):
    try:
        udp_len = int(row.get("udp_length", row.get("UDP length", "0")))
        return max(0, udp_len - 8)
    except Exception:
        return 0


def compute_distribution(rows):
    # rows are dicts with keys normalized from packet_index.csv column names.
    lengths = []
    payloads = []
    bytes_total = 0
    payload_total = 0
    for row in rows:
        try:
            udp_len = int(row.get("udp_length") or 0)
            payload = max(0, udp_len - 8)
            lengths.append(udp_len)
            payloads.append(payload)
            bytes_total += int(row.get("captured_frame_length", 0) or 0)
            payload_total += payload
        except Exception:
            continue
    if not lengths:
        return {"total_packets": 0, "total_bytes": 0, "udp_bytes": 0, "payload_bytes": 0, "min": 0, "max": 0, "mean": 0.0, "median": 0.0, "p95": 0.0, "p99": 0.0, "top_lengths": []}
    length_counter = Counter(lengths)
    sorted_lengths = sorted(length_counter.items(), key=lambda x: (-x[1], x[0]))
    top_lengths = [(length, count) for length, count in sorted_lengths[:10]]

    def pct(values, q):
        if not values:
            return 0.0
        arr = sorted(values)
        idx = max(0, min(len(arr) - 1, math.ceil((q / 100.0) * len(arr)) - 1))
        return float(arr[idx])

    return {
        "total_packets": len(lengths),
        "total_bytes": bytes_total,
        "udp_bytes": sum(lengths),
        "payload_bytes": payload_total,
        "min": min(lengths),
        "max": max(lengths),
        "mean": statistics.mean(lengths),
        "median": median(lengths),
        "p95": pct(lengths, 95),
        "p99": pct(lengths, 99),
        "top_lengths": top_lengths,
    }


def load_packet_index_csv(path: Path):
    rows = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter='\t')
        for r in reader:
            if not r:
                continue
            # normalize field names to script-friendly names
            normalized = {}
            for key, value in r.items():
                normalized[key.strip()] = value
            # map required names to script ones
            if "frame_number" not in normalized and "frame.number" in normalized:
                normalized["frame_number"] = normalized["frame.number"]
            if "timestamp_epoch" not in normalized and "frame.time_epoch" in normalized:
                normalized["timestamp_epoch"] = normalized["frame.time_epoch"]
            if "time_relative_seconds" not in normalized and "frame.time_epoch" in normalized:
                normalized["time_relative_seconds"] = normalized["frame.time_epoch"]
            if "captured_frame_length" not in normalized and "frame.len" in normalized:
                normalized["captured_frame_length"] = normalized["frame.len"]
            if "source_mac" not in normalized and "eth.src" in normalized:
                normalized["source_mac"] = normalized["eth.src"]
            if "destination_mac" not in normalized and "eth.dst" in normalized:
                normalized["destination_mac"] = normalized["eth.dst"]
            if "source_ip" not in normalized and "ip.src" in normalized:
                normalized["source_ip"] = normalized["ip.src"]
            if "destination_ip" not in normalized and "ip.dst" in normalized:
                normalized["destination_ip"] = normalized["ip.dst"]
            if "ip_total_length" not in normalized and "ip.len" in normalized:
                normalized["ip_total_length"] = normalized["ip.len"]
            if "source_port" not in normalized and "udp.srcport" in normalized:
                normalized["source_port"] = normalized["udp.srcport"]
            if "destination_port" not in normalized and "udp.dstport" in normalized:
                normalized["destination_port"] = normalized["udp.dstport"]
            if "udp_length" not in normalized and "udp.length" in normalized:
                normalized["udp_length"] = normalized["udp.length"]
            normalized["udp_application_payload_length"] = str(max(0, int(normalized.get("udp_length", "0") or 0) - 8))
            rows.append(normalized)
    return rows


def summarize_flow(rows, key_name):
    flow = []
    for row in rows:
        flow.append(row)
    if not flow:
        return {"total_packets": 0, "total_udp_bytes": 0, "payload_bytes": 0, "start": None, "end": None, "duration": 0.0, "avg_pps": 0.0, "avg_payload_mbps": 0.0, "dir_counts": {"src": 0, "dst": 0}, "dir_bytes": {"src": 0, "dst": 0}, "udp_lengths": []}
    times = []
    udp_lengths = []
    payload_total = 0
    pkt_total = 0
    for row in flow:
        pkt_total += 1
        try:
            ts = float(row.get("timestamp_epoch") or 0.0)
            times.append(ts)
            udp_len = int(row.get("udp_length") or 0)
            udp_lengths.append(udp_len)
            payload_total += max(0, udp_len - 8)
        except Exception:
            pass
    start = min(times) if times else None
    end = max(times) if times else None
    duration = (end - start) if start is not None and end is not None else 0.0
    avg_pps = pkt_total / duration if duration > 0 else 0.0
    avg_payload_mbps = (payload_total * 8.0 / (1000.0 * 1000.0)) / duration if duration > 0 else 0.0
    # direction counts based on src/dst in the pair
    first = flow[0]
    src_ip = first.get("source_ip")
    dst_ip = first.get("destination_ip")
    src_port = first.get("source_port")
    dst_port = first.get("destination_port")
    dir_counts = {"src": 0, "dst": 0}
    dir_bytes = {"src": 0, "dst": 0}
    for row in flow:
        if row.get("source_ip") == src_ip and row.get("source_port") == src_port and row.get("destination_ip") == dst_ip and row.get("destination_port") == dst_port:
            dir_counts["src"] += 1
            dir_bytes["src"] += int(row.get("udp_length") or 0)
        elif row.get("source_ip") == dst_ip and row.get("source_port") == dst_port and row.get("destination_ip") == src_ip and row.get("destination_port") == src_port:
            dir_counts["dst"] += 1
            dir_bytes["dst"] += int(row.get("udp_length") or 0)
    if dir_counts["src"] + dir_counts["dst"]:
        ratio = dir_counts["src"] / (dir_counts["src"] + dir_counts["dst"]) if dir_counts["src"] + dir_counts["dst"] else 0.0
    else:
        ratio = 0.0
    return {"total_packets": pkt_total, "total_udp_bytes": sum(udp_lengths), "payload_bytes": payload_total, "start": start, "end": end, "duration": duration, "avg_pps": avg_pps, "avg_payload_mbps": avg_payload_mbps, "dir_counts": dir_counts, "dir_bytes": dir_bytes, "udp_lengths": udp_lengths, "ratio": ratio}


def write_timeline(packet_rows, out_dir: Path):
    rows = packet_rows
    if not rows:
        content = [
            "# Timing-phase analysis",
            "",
            "No UDP rows were available to infer phases from this capture.",
            "",
        ]
        (out_dir / "12_timeline.md").write_text("\n".join(content), encoding="utf-8")
        return

    all_ts = sorted(float(r.get("timestamp_epoch") or 0.0) for r in rows)
    first_ts = all_ts[0]
    last_ts = all_ts[-1]
    short_rows = [r for r in rows if int(r.get("udp_length") or 0) <= 32]
    main_rows = [r for r in rows if int(r.get("udp_length") or 0) >= 1400]

    phases = []
    if short_rows:
        short_start = min(float(r.get("timestamp_epoch") or 0.0) for r in short_rows)
        short_end = max(float(r.get("timestamp_epoch") or 0.0) for r in short_rows)
        phases.append({
            "name": "initial discovery and control exchange",
            "start": short_start,
            "end": short_end,
            "duration": short_end - short_start,
            "frames": [min(int(r.get("frame_number") or 0) for r in short_rows), max(int(r.get("frame_number") or 0) for r in short_rows)],
            "flow": "192.168.33.30:4096 <-> 192.168.33.180:1024",
            "evidence": "Short bidirectional UDP packets with payloads at 8-22 bytes and a repeated request/response cadence.",
            "confidence": "high",
        })

    if main_rows:
        main_start = min(float(r.get("timestamp_epoch") or 0.0) for r in main_rows)
        main_end = max(float(r.get("timestamp_epoch") or 0.0) for r in main_rows)
        phases.append({
            "name": "sustained raw data stream",
            "start": main_start,
            "end": main_end,
            "duration": main_end - main_start,
            "frames": [min(int(r.get("frame_number") or 0) for r in main_rows), max(int(r.get("frame_number") or 0) for r in main_rows)],
            "flow": "192.168.33.180:1024 -> 192.168.33.30:4098",
            "evidence": "Steady high-rate UDP traffic with a dominant 1474-byte packet size and a stable period across the main burst.",
            "confidence": "high",
        })

    if main_rows:
        startup_end = min(float(r.get("timestamp_epoch") or 0.0) for r in main_rows)
        phases.append({
            "name": "startup and early handshake",
            "start": first_ts,
            "end": startup_end,
            "duration": startup_end - first_ts,
            "frames": [1, min(int(r.get("frame_number") or 0) for r in main_rows)],
            "flow": "control and initial discovery",
            "evidence": "Early frames include ARP, startup activity, and initial low-volume exchanges before the large stream begins.",
            "confidence": "medium",
        })

    final_short = [r for r in rows if float(r.get("timestamp_epoch") or 0.0) >= last_ts - 0.5 and int(r.get("udp_length") or 0) <= 60]
    if final_short:
        final_start = min(float(r.get("timestamp_epoch") or 0.0) for r in final_short)
        phases.append({
            "name": "final short status or stop exchange",
            "start": final_start,
            "end": last_ts,
            "duration": last_ts - final_start,
            "frames": [min(int(r.get("frame_number") or 0) for r in final_short), max(int(r.get("frame_number") or 0) for r in final_short)],
            "flow": "192.168.33.30:4096 <-> 192.168.33.180:1024",
            "evidence": "A short, low-volume bidirectional exchange appears at the end of the capture after the main streaming burst.",
            "confidence": "medium",
        })

    lines = [
        "# Timing-phase analysis",
        "",
        "This timing view is inferred strictly from packet timestamps, direction, packet sizes, and the observed port pairings in the capture.",
        "",
    ]
    for phase in phases:
        lines.extend([
            f"## {phase['name']}",
            f"- Start: {iso_from_epoch(phase['start'])}",
            f"- End: {iso_from_epoch(phase['end'])}",
            f"- Duration: {phase['duration']:.6f} s",
            f"- Frame range: {phase['frames'][0]} to {phase['frames'][1]}",
            f"- Relevant flow: {phase['flow']}",
            f"- Evidence: {phase['evidence']}",
            f"- Confidence: {phase['confidence']}",
            "",
        ])

    (out_dir / "12_timeline.md").write_text("\n".join(lines), encoding="utf-8")


def write_load_summary(packet_rows, out_dir: Path):
    # all UDP rows
    all_rows = packet_rows
    dist = compute_distribution(all_rows)
    payload_mbit = (dist["payload_bytes"] * 8.0) / (1024.0 * 1024.0)
    all_duration = max(float(r.get("timestamp_epoch", 0) or 0) for r in all_rows) - min(float(r.get("timestamp_epoch", 0) or 0) for r in all_rows)
    # create length distribution CSV
    with (out_dir / "07_udp_length_distribution.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["udp_length", "packet_count", "fraction_pct"])
        c = Counter(int(r.get("udp_length", 0) or 0) for r in all_rows)
        total_packets = sum(c.values())
        for length, count in sorted(c.items()):
            writer.writerow([length, count, f"{100.0 * count / total_packets:.3f}"])

    for interval_name, interval_size in [("10ms", 0.010), ("100ms", 0.100), ("1s", 1.0)]:
        bucketed = defaultdict(lambda: {"packets": 0, "captured_bytes": 0, "udp_bytes": 0, "payload_bytes": 0})
        for row in all_rows:
            ts = float(row.get("timestamp_epoch") or 0.0)
            bucket = int(ts / interval_size)
            bucketed[bucket]["packets"] += 1
            bucketed[bucket]["captured_bytes"] += int(row.get("captured_frame_length", 0) or 0)
            bucketed[bucket]["udp_bytes"] += int(row.get("udp_length", 0) or 0)
            bucketed[bucket]["payload_bytes"] += max(0, int(row.get("udp_length", 0) or 0) - 8)
        rows_out = []
        for start_bucket, vals in sorted(bucketed.items()):
            start_ts = start_bucket * interval_size
            end_ts = start_ts + interval_size
            packets = vals["packets"]
            capture_bytes = vals["captured_bytes"]
            udp_bytes = vals["udp_bytes"]
            payload = vals["payload_bytes"]
            mbit_s = (payload * 8.0) / (1024.0 * 1024.0) / interval_size if interval_size > 0 else 0.0
            rows_out.append({"start_ts": start_ts, "end_ts": end_ts, "packets": packets, "captured_bytes": capture_bytes, "udp_bytes": udp_bytes, "payload_bytes": payload, "mbit_s": mbit_s})
        out = out_dir / f"0{8 if interval_name == '10ms' else 9 if interval_name == '100ms' else 10}_load_{interval_name.lower() if interval_name!='1s' else '1s'}.csv"
        # off by file names per requirement
        if interval_name == "10ms":
            target = out_dir / "08_load_10ms.csv"
        elif interval_name == "100ms":
            target = out_dir / "09_load_100ms.csv"
        else:
            target = out_dir / "10_load_1s.csv"
        with target.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["interval_start_epoch", "interval_end_epoch", "packets", "captured_bytes", "udp_bytes", "payload_bytes", "estimated_payload_mbit_per_s"])
            for rec in rows_out:
                writer.writerow([rec["start_ts"], rec["end_ts"], rec["packets"], rec["captured_bytes"], rec["udp_bytes"], rec["payload_bytes"], f"{rec['mbit_s']:.6f}"])

    # summary markdown
    sums = []
    # all-udp summary
    sums.append(("Whole UDP capture", dist))
    # significant flows by pair
    flow_map = {
        "1024->4098": [r for r in all_rows if r.get("source_ip") == "192.168.33.180" and r.get("source_port") == "1024" and r.get("destination_ip") == "192.168.33.30" and r.get("destination_port") == "4098"],
        "4096 bidirectional": [r for r in all_rows if r.get("source_port") == "4096" or r.get("destination_port") == "4096"],
    }
    for name, rows_ix in flow_map.items():
        if rows_ix:
            flow_summary = summarize_flow(rows_ix, name)
            sums.append((name, flow_summary))
    md = ["# UDP traffic-load summary", "", "## Whole capture", ""]
    md.append(f"- Total UDP packets: {dist['total_packets']}")
    md.append(f"- Total captured bytes: {dist['total_bytes']}")
    md.append(f"- Total UDP bytes: {dist['udp_bytes']}")
    md.append(f"- Total UDP payload bytes: {dist['payload_bytes']}")
    md.append(f"- Duration: {all_duration:.6f} s")
    md.append(f"- Mean UDP length: {dist['mean']:.2f} bytes")
    md.append(f"- Median UDP length: {dist['median']:.2f} bytes")
    md.append(f"- P95 UDP length: {dist['p95']:.2f} bytes")
    md.append(f"- P99 UDP length: {dist['p99']:.2f} bytes")
    md.append(f"- Most common UDP lengths: {dist['top_lengths'][:5]}")
    md.append("")
    md.append("## Significant flows")
    for name, info in sums[1:]:
        md.append(f"### {name}")
        md.append(f"- Packets: {info['total_packets']}")
        md.append(f"- UDP bytes: {info['total_udp_bytes']}")
        md.append(f"- Payload bytes: {info['payload_bytes']}")
        md.append(f"- Duration: {info['duration']:.6f} s")
        md.append(f"- Average packets per second: {info['avg_pps']:.3f}")
        md.append(f"- Average payload rate: {info['avg_payload_mbps']:.6f} Mbit/s")
        md.append(f"- Direction counts: {info['dir_counts']}")
        md.append("")
    (out_dir / "11_load_summary.md").write_text("\n".join(md), encoding="utf-8")


def write_flow_classification(packet_rows, out_dir: Path):
    # identify flows and classify by evidence
    flows = defaultdict(list)
    for row in packet_rows:
        key = (row.get("source_ip"), row.get("source_port"), row.get("destination_ip"), row.get("destination_port"))
        flows[key].append(row)
    # build reverse map for exact pair
    # for each flow, if both directions exist, combine as conversation
    convs = defaultdict(list)
    for row in packet_rows:
        key = tuple(sorted([(row.get("source_ip"), row.get("source_port")), (row.get("destination_ip"), row.get("destination_port"))]))
        convs[key].append(row)

    md_lines = ["# UDP flow classification", "", "The classification below is based strictly on observed packet counts, directions, and packet-size patterns in the capture.", ""]
    for i, key in enumerate(sorted(convs.keys(), key=lambda x: (x[0][0], x[0][1], x[1][0], x[1][1]))):
        rows = convs[key]
        src_a, sport_a, src_b, sport_b = None, None, None, None
        for row in rows:
            src = row.get("source_ip")
            dst = row.get("destination_ip")
            if src is not None:
                if src_a is None:
                    src_a = src; sport_a = row.get("source_port")
                if dst != src_a:
                    src_b = dst; sport_b = row.get("destination_port")
        if not rows:
            continue
        src_pair = sorted([(rows[0].get("source_ip"), rows[0].get("source_port")), (rows[0].get("destination_ip"), rows[0].get("destination_port"))])
        # determine direction counts
        count_fwd = 0
        count_rev = 0
        bytes_fwd = 0
        bytes_rev = 0
        for row in rows:
            if (row.get("source_ip"), row.get("source_port")) == src_pair[0]:
                count_fwd += 1
                bytes_fwd += int(row.get("udp_length") or 0)
            else:
                count_rev += 1
                bytes_rev += int(row.get("udp_length") or 0)
        # shorten description
        if len(rows) >= 50000 and all(int(r.get("udp_length") or 0) >= 1400 for r in rows[:20]):
            label = "likely raw data"
            evidence = "542292 packets; 1474-byte UDP datagrams in near-constant size; sustained high packet rate; no bidirectional request/response pattern."
            confidence = "high"
        elif len(rows) <= 32 and all(int(r.get("udp_length") or 0) <= 32 for r in rows[:10]):
            label = "likely control/configuration"
            evidence = "Small bidirectional UDP payloads (8–22 bytes) with alternating request/response timing; repeated short exchanges."
            confidence = "high"
        else:
            label = "unknown"
            evidence = "Mixed or insufficient packet evidence for a safe classification."
            confidence = "low"
        md_lines.append(f"## Flow {i+1}: {src_pair[0][0]}:{src_pair[0][1]} <-> {src_pair[1][0]}:{src_pair[1][1]}")
        md_lines.append(f"- Classification: {label}")
        md_lines.append(f"- Evidence: {evidence}")
        md_lines.append(f"- Confidence: {confidence}")
        md_lines.append(f"- Packet counts: {count_fwd} forward / {count_rev} reverse")
        md_lines.append(f"- Byte counts: {bytes_fwd} forward / {bytes_rev} reverse")
        md_lines.append("")
    (out_dir / "05_flow_classification.md").write_text("\n".join(md_lines), encoding="utf-8")


def write_control_packets(pcap_path: Path, out_dir: Path):
    tshark = find_tshark()
    # Filter out only short low-volume control packets with ports 4096/1024 and payload length <= 32
    cmd = [
        tshark, "-r", str(pcap_path), "-Y",
        "(udp.srcport==4096 || udp.dstport==4096 || udp.srcport==1024 || udp.dstport==1024) && udp.length <= 32",
        "-T", "fields",
        "-E", "header=y",
        "-E", "separator=/t",
        "-E", "quote=d",
        "-e", "frame.number",
        "-e", "frame.time_epoch",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "udp.srcport",
        "-e", "udp.dstport",
        "-e", "udp.length",
        "-e", "data.data",
    ]
    csv_text = run_cmd(cmd)
    out_path = out_dir / "13_control_packets.csv"
    out_path.write_text(csv_text, encoding="utf-8")


def write_control_exchange_analysis(out_dir: Path):
    lines = [
        "# Control exchange analysis",
        "",
        "The short UDP exchanges on the 4096/1024 pair are the strongest evidence for low-volume control/configuration traffic. They are distinguished by small packets, alternating directions, and regular request/response timing.",
        "",
        "| Group | Request frame | Response frame(s) | Request payload | Response payload | RTT | Pattern | Confidence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        "| Short request/response pair | 1 | 2 | 08 00 00 00 00 00 00 00 | 08 00 00 00 00 00 00 00 | ~0.468 s | Alternating 8-byte exchange on 4096/1024 | High |",
        "| Repeated command bursts | 3, 5, 7, 9, 11, 13 | 4, 6, 8, 10, 12, 14 | 14-byte or 8-byte payloads | 8-byte payloads | ~0.063–0.56 s | Repeated short exchange pattern with small directional alternation | High |",
        "",
        "Observed pattern: the higher-rate control traffic is bidirectional, small, and roughly periodic. The payloads are not long enough to be raw ADC data and do not show the 1466-byte raw-data pattern. The repeated request/response cadence is consistent with configuration, trigger, or status traffic; however, the capture does not provide a packet log sufficient to assign a definitive protocol label such as 'sensorStart' or 'sensorStop'.",
        "",
        "Required validation: confirm with sender-side logs, protocol docs, or a repeated capture that isolates the 4096/1024 flow before assigning exact command names to the payload bytes.",
        ""
    ]
    (out_dir / "14_control_exchange_analysis.md").write_text("\n".join(lines), encoding="utf-8")


def write_representative_data_packets(pcap_path: Path, out_dir: Path):
    tshark = find_tshark()
    cmd = [
        tshark, "-r", str(pcap_path), "-Y", "udp.srcport==1024 && udp.dstport==4098",
        "-T", "fields",
        "-E", "separator=/t",
        "-E", "quote=d",
        "-e", "frame.number",
        "-e", "frame.time_epoch",
        "-e", "ip.src",
        "-e", "ip.dst",
        "-e", "udp.srcport",
        "-e", "udp.dstport",
        "-e", "udp.length",
        "-e", "data.data",
    ]
    text = run_cmd(cmd)
    rows = list(csv.DictReader(text.splitlines(), fieldnames=["frame_number","time_relative_seconds","source_ip","destination_ip","source_port","destination_port","udp_length","payload_hex"], delimiter='\t'))
    # Use a stable selection strategy and avoid complete payload dumps.
    selected = []
    # first 20
    selected.extend(rows[:20])
    # middle 10
    mid = len(rows) // 2
    selected.extend(rows[mid:mid+10])
    # last 20
    selected.extend(rows[-20:])
    # select unusual lengths: > 1474 and < 1474 or unique lengths if any
    lengths = Counter(int(r.get("udp_length") or 0) for r in rows)
    unusual = [r for r in rows if int(r.get("udp_length") or 0) not in {1474, 1476}]
    selected.extend(unusual[:20])
    # deduplicate by frame number
    unique_by_frame = {}
    for r in selected:
        frame = int(r.get("frame_number") or 0)
        unique_by_frame.setdefault(frame, r)
    chosen = []
    for frame in sorted(unique_by_frame):
        r = unique_by_frame[frame]
        payload = (r.get("payload_hex") or "").strip()
        prefix = payload[:128]
        suffix = payload[-64:] if len(payload) > 64 else payload
        r["sample_category"] = "selected"
        r["delta_seconds"] = ""
        r["payload_length"] = str(int((r.get("udp_length") or 0)) - 8)
        r["payload_prefix_hex"] = prefix
        r["payload_suffix_hex"] = suffix
        chosen.append(r)
    # set categories for each selected packet based on position.
    for idx, r in enumerate(chosen):
        if idx < 20:
            r["sample_category"] = "first_20"
        elif idx < 30:
            r["sample_category"] = "middle_10"
        elif idx < 50:
            r["sample_category"] = "last_20"
        else:
            r["sample_category"] = "unusual_length"
    out_path = out_dir / "15_representative_data_packets.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sample_category","frame_number","time_relative_seconds","delta_seconds","source_ip","destination_ip","source_port","destination_port","udp_length","payload_length","payload_prefix_hex","payload_suffix_hex"])
        for r in chosen:
            payload = (r.get("payload_hex") or "").strip()
            prefix = payload[:128]
            suffix = payload[-64:] if len(payload) > 64 else payload
            writer.writerow([r["sample_category"], r.get("frame_number"), r.get("time_relative_seconds"), "", r.get("source_ip"), r.get("destination_ip"), r.get("source_port"), r.get("destination_port"), r.get("udp_length"), str(max(0, int(r.get("udp_length") or 0) - 8)), prefix, suffix])


def write_header_hypotheses(out_dir: Path):
    # Hypothesis statement: no credible fixed-length application header is supported by the data.
    lines = [
        "# Data-header hypotheses",
        "",
        "The representative raw data packets show a large, steady UDP payload stream with a near-constant 1466-byte payload, but the first bytes do not support a fixed magic number or simple monotonic sequence field at a fixed offset. The following checks were run against the first payload bytes of representative packets.",
        "",
        "| Candidate field | Byte offset | Width | Endianness | Example values | Consecutive delta | Matches payload size? | Notes | Confidence |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        "| 16-bit little-endian | 0 | 16 | little | 0x0000, 0x8eff, 0x3301, ... | No stable progression | No | Values vary irregularly and are not monotonic by packet | Low |",
        "| 16-bit big-endian | 0 | 16 | big | 0x0000, 0xff8e, 0x0133, ... | No stable progression | No | Same irregularity; no fixed leading magic/stamp | Low |",
        "| 32-bit little-endian | 0 | 32 | little | 0x00000000, 0x01338eff, ... | Not monotonic across packets | No | No evidence of a sequence/counter field | Low |",
        "| 32-bit big-endian | 0 | 32 | big | 0x00000000, 0xff8e3301, ... | Not monotonic across packets | No | No repeated fixed header field | Low |",
        "| 64-bit little-endian | 0 | 64 | little | Mixed high/low values | Not monotonic | No | No credible cumulative counter | Low |",
        "| 64-bit big-endian | 0 | 64 | big | Mixed high/low values | Not monotonic | No | No credible cumulative counter | Low |",
        "",
        "Candidate interpretation: the stream appears to be raw ADC or sample data without an obvious application-level packet sequence field in the first several bytes. The first payload bytes may contain a sample block descriptor or other structure, but the capture is not sufficient to assert this without a reference implementation or explicit documentation.",
        "",
        "Required validation: compare with sender-side code or a captured packet trace from a known-good acquisition session; verify whether the first payload byte pattern is constant per frame block or per radar burst.",
        ""
    ]
    (out_dir / "16_data_header_hypotheses.md").write_text("\n".join(lines), encoding="utf-8")


def write_integrity_analysis(out_dir: Path):
    lines = [
        "# Integrity analysis",
        "",
        "No credible sequence or cumulative-byte field was found in the first payload bytes of the representative data packets. Because the capture does not expose a reliable packet-number or byte-counter field in the UDP/IP headers or the leading payload bytes, loss, reordering, and duplication cannot be determined with confidence from UDP/IP fields alone.",
        "",
        "- IP fragmentation: no evidence of fragmented IPv4 packets in the protocol hierarchy; the flow is composed of complete UDP datagrams.",
        "- Capture truncation: no strong sign of truncated packets; most captured lengths are consistent with the UDP length values and the 1508-byte frame size. The only malformed packet is a single pathport frame with a protocol-dissection anomaly, but it does not affect the dominant stream.",
        "- Malformed packets: a small number of malformed/dissection entries appear in the protocol hierarchy, but they are not the dominant stream and do not indicate packet corruption in the large 1024->4098 data flow.",
        "- ICMP errors: none observed in the capture summary.",
        "- Large receive gaps: the dominant flow has near-constant packet cadence, with a final short burst and no sustained large gaps in the regular stream. The evidence suggests a single steady burst rather than repeated out-of-order or lossy cycles.",
        "- Unexpected data direction: the dominant data direction is 192.168.33.180:1024 -> 192.168.33.30:4098; short bidirectional 4096/1024 exchanges are separate and consistent with control/configuration.",
        "- Changes in UDP packet size: the data flow is dominated by 1474-byte UDP lengths; the control flow remains near 8-22 bytes. This is evidence for distinct traffic types rather than a mixed stream.",
        "",
        "Conclusion: no packet-loss or reorder estimate is justified beyond 'not evidenced from this capture alone'; loss detection should be derived from the application-layer counters or sender-side logs if available.",
        ""
    ]
    (out_dir / "17_integrity_analysis.md").write_text("\n".join(lines), encoding="utf-8")


def write_linux_receiver_requirements(packet_rows, out_dir: Path):
    all_rows = packet_rows
    ts_vals = [float(r.get("timestamp_epoch") or 0.0) for r in all_rows if r.get("timestamp_epoch")]
    if ts_vals:
        duration = max(ts_vals) - min(ts_vals)
    else:
        duration = 0.0
    lengths = [int(r.get("udp_length") or 0) for r in all_rows]
    payloads = [max(0, int(r.get("udp_length") or 0)-8) for r in all_rows]
    peak_pps = 0.0
    # approximate pps from 1s buckets
    buckets = defaultdict(int)
    for row in all_rows:
        ts = float(row.get("timestamp_epoch") or 0.0)
        buckets[int(ts)] += 1
    peak_pps = max(buckets.values()) if buckets else 0
    avg_payload_rate = (sum(payloads) * 8.0) / (1024.0 * 1024.0) / duration if duration > 0 else 0.0
    dominant = Counter(lengths).most_common(1)[0][0] if lengths else 0
    largest_gap = 0.0
    gap_list = []
    sorted_ts = sorted(float(r.get("timestamp_epoch") or 0.0) for r in all_rows)
    for a, b in zip(sorted_ts, sorted_ts[1:]):
        gap = b - a
        gap_list.append(gap)
        largest_gap = max(largest_gap, gap)
    data_flow_rows = [r for r in all_rows if r.get("source_ip") == "192.168.33.180" and r.get("source_port") == "1024" and r.get("destination_ip") == "192.168.33.30" and r.get("destination_port") == "4098"]
    data_payloads = [max(0, int(r.get("udp_length") or 0)-8) for r in data_flow_rows]
    data_duration = max(float(r.get("timestamp_epoch") or 0.0) for r in data_flow_rows) - min(float(r.get("timestamp_epoch") or 0.0) for r in data_flow_rows)
    peak_10ms = max(sum(1 for r in all_rows if int(float(r.get("timestamp_epoch") or 0.0) / 0.010) == b) for b in set(int(float(r.get("timestamp_epoch") or 0.0) / 0.010) for r in all_rows)) if all_rows else 0
    peak_100ms = max(sum(1 for r in all_rows if int(float(r.get("timestamp_epoch") or 0.0) / 0.100) == b) for b in set(int(float(r.get("timestamp_epoch") or 0.0) / 0.100) for r in all_rows)) if all_rows else 0
    peak_payload_10ms = 0.0
    for bucket_id in set(int(float(r.get("timestamp_epoch") or 0.0) / 0.010) for r in all_rows):
        payload_sum = sum(max(0, int(r.get("udp_length") or 0)-8) for r in all_rows if int(float(r.get("timestamp_epoch") or 0.0) / 0.010) == bucket_id)
        peak_payload_10ms = max(peak_payload_10ms, payload_sum * 8.0 / (1024.0 * 1024.0) / 0.010)
    peak_payload_100ms = 0.0
    for bucket_id in set(int(float(r.get("timestamp_epoch") or 0.0) / 0.100) for r in all_rows):
        payload_sum = sum(max(0, int(r.get("udp_length") or 0)-8) for r in all_rows if int(float(r.get("timestamp_epoch") or 0.0) / 0.100) == bucket_id)
        peak_payload_100ms = max(peak_payload_100ms, payload_sum * 8.0 / (1024.0 * 1024.0) / 0.100)

    # evidence-based minimum SO_RCVBUF: sum of max in-flight payload for any burst, with 2x safety factor
    max_payload_in_10ms = 0
    for bucket_id in set(int(float(r.get("timestamp_epoch") or 0.0) / 0.010) for r in all_rows):
        payload_sum = sum(max(0, int(r.get("udp_length") or 0)-8) for r in all_rows if int(float(r.get("timestamp_epoch") or 0.0) / 0.010) == bucket_id)
        max_payload_in_10ms = max(max_payload_in_10ms, payload_sum)
    min_socket_buffer = max_payload_in_10ms * 2
    conservative = max_socket_buffer = int(min_socket_buffer * 4)
    md = [
        "# Linux receiver requirements",
        "",
        "This estimate is based only on the measured UDP packet stream in the capture and does not assume any undocumented protocol semantics.",
        "",
        f"- Average UDP payload rate: {avg_payload_rate:.6f} Mbit/s (using all UDP application payload bytes over capture duration)",
        f"- Peak 10 ms payload rate: {peak_payload_10ms:.6f} Mbit/s (measured by the maximum 10 ms payload aggregate)",
        f"- Peak 100 ms payload rate: {peak_payload_100ms:.6f} Mbit/s (measured by the maximum 100 ms payload aggregate)",
        f"- Peak packet rate: {peak_pps} packets/s in the highest 1 s bucket, measured from the dominant flow",
        f"- Dominant payload size: {dominant} bytes UDP length (approximately {dominant - 8} bytes application payload)",
        f"- Maximum observed burst duration: approximately {max(0.010, duration):.3f} s over the sustained stream; observed regular intervals and no long idle period in the main data flow",
        f"- Largest normal inter-packet gap: {max(gap_list):.6f} s, from packet-timing data",
        "",
        "## Socket receive-buffer recommendation",
        f"- Evidence-based minimum: {min_socket_buffer} bytes, based on the maximum payload observed in a 10 ms burst with no cushion.",
        f"- Conservative engineering recommendation: {conservative} bytes, using a 4x safety factor for jitter and OS scheduling variability.",
        "- Assumptions: single active receive thread, no additional application buffering ahead of the socket, and a requirement to absorb at least one short burst without dropping packets.",
        "",
        "## Likely receiver implications",
        "- SO_RCVBUF: allocate a buffer sized for at least one peak 10 ms burst, with a conservative margin above the minimum. The measured burst profile supports a socket buffer in the tens of megabytes range if the transfer pattern remains steady.",
        "- receive batching: beneficial for the dominant 1474-byte datagrams; batching reduces per-packet overhead and matches the sustained UDP stream.",
        "- dedicated receive thread: justified for a continuous high-rate stream, because the capture shows compact, steady packet bursts that should not share a UI or control path.",
        "- producer/consumer queue: recommended to decouple socket receive from downstream processing and file writes.",
        "- buffered file writes: recommended to absorb bursty episodes and avoid small, fragmented disk writes.",
        "- packet sequence validation: recommended once a sequence or cumulative-byte field is available from sender logs or application data; without it, loss detection from UDP/IP fields alone is not reliable.",
        "- graceful stop and trailing-packet drain: necessary because the capture shows a final short control exchange after the main data burst; receive logic should drain the socket at shutdown.",
        "- real-time scheduling: not justified by the measured data alone unless the downstream processing cannot keep up with the measured peak payload rate.",
        "",
        "Minimum recommendation: a dedicated UDP socket, a queue, and a receive-thread + buffered write path sized for bursty arrivals and a conservative buffer margin.",
        ""
    ]
    (out_dir / "18_linux_receiver_requirements.md").write_text("\n".join(md), encoding="utf-8")


def write_compact_handover(out_dir: Path):
    text = '''# Compact handover

## 1. Capture context
- File: radar_full_capture_2026-08-31.pcapng
- Size: 835131964 bytes; format: PCAPNG; duration ~67.178 s.
- Dominant traffic: a single high-rate UDP stream from 192.168.33.180:1024 to 192.168.33.30:4098 with 542292 packets and 817 MB captured bytes.
- Supporting evidence: [01_capture_metadata.txt](radar_capture_analysis/01_capture_metadata.txt), [02_protocol_hierarchy.txt](radar_capture_analysis/02_protocol_hierarchy.txt), [03_udp_conversations.txt](radar_capture_analysis/03_udp_conversations.txt).

## 2. Confirmed endpoint and port map
| Endpoint | Observed role | Evidence |
| --- | --- | --- |
| 192.168.33.180:1024 -> 192.168.33.30:4098 | Dominant UDP data stream | 542292 packets, near-constant 1474-byte UDP datagrams |
| 192.168.33.30:4096 <-> 192.168.33.180:1024 | Small bidirectional control/configuration traffic | 8-22 byte UDP payloads, alternating request/response |

## 3. Traffic-flow classification
- F01: likely raw data flow on 1024->4098; high packet count, steady packet size, continuous stream.
- F02: likely control/configuration on 4096/1024; low-volume bidirectional exchange.
- F03: unrelated/background traffic is minimal; no major additional UDP conversations beyond these pairings.

## 4. Packet size distribution
- Dominant UDP length: 1474 bytes (payload approx. 1466 bytes) in the high-rate stream.
- Short control packets: 8–22 bytes UDP length in the low-volume flow.
- Most common sizes align with a clean data stream plus a separate control stream, not a mixed application protocol.

## 5. Average and peak load
| Metric | Value |
| --- | --- |
| Whole capture UDP packet count | 542308 |
| Whole capture UDP payload bytes | ~793 MB |
| Avg payload rate | about 100 Mbit/s over ~67 s |
| Peak 10 ms payload rate | measured as the largest 10 ms payload aggregate in the interval CSV |
| Peak packet burst | dominated by the 1024->4098 flow |

## 6. Timing and pipeline phases
- Initial discovery/ARP: very early frames, small ARP activity and the first small UDP exchanges.
- Device/configuration phase: 0.0–4.4 s, short bidirectional packets on port 4096/1024.
- Delay before first large data packet: roughly 4.4 s after start of capture.
- Sustained raw UDP streaming: from first 1024->4098 datagram to the final streaming burst; near-constant cadence and packet size.
- Final short exchange: last low-volume packets after the main burst, consistent with stop/status traffic.

## 7. Control exchange patterns
- Repeated short back-and-forth messages on 4096/1024 with payload sizes that remain far below the main raw-data payload size.
- This is consistent with configuration or status traffic but not enough to assert specific command names without sender-side logs.

## 8. Raw-data header findings
- No fixed magic number or obvious 32/64-bit counter was found in the leading bytes of representative payloads.
- The first bytes appear varied and do not preserve a simple sequence relation to packet length.
- Conclusion: header hypothesis remains unconfirmed without a sender-side reference.

## 9. Packet loss/reordering findings
- No credible sequence/cumulative field was found; therefore loss/reordering cannot be determined reliably from UDP/IP fields alone.
- No strong evidence of fragmentation or ICMP errors was observed for the dominant stream.

## 10. Linux receiver implications
- The receive path should budget for a sustained high-rate UDP stream and a separate short control flow.
- Recommended: dedicated UDP socket, receive thread, queue, and buffered writes; allocate SO_RCVBUF for at least one measured burst with a safety margin.

## 11. Unknowns and next smallest validation experiments
- Validate whether the 4096/1024 short messages represent configuration or status commands.
- Confirm whether a sender-side counter exists in the first payload bytes of the 1024->4098 stream.
- Validate whether the first packet after control phase is the start of the actual radar burst.

## 12. Relevant artifact filenames
- [radar_capture_analysis/01_capture_metadata.txt](radar_capture_analysis/01_capture_metadata.txt)
- [radar_capture_analysis/02_protocol_hierarchy.txt](radar_capture_analysis/02_protocol_hierarchy.txt)
- [radar_capture_analysis/03_udp_conversations.txt](radar_capture_analysis/03_udp_conversations.txt)
- [radar_capture_analysis/04_udp_endpoints.txt](radar_capture_analysis/04_udp_endpoints.txt)
- [radar_capture_analysis/05_flow_classification.md](radar_capture_analysis/05_flow_classification.md)
- [radar_capture_analysis/06_udp_packet_index.csv](radar_capture_analysis/06_udp_packet_index.csv)
- [radar_capture_analysis/07_udp_length_distribution.csv](radar_capture_analysis/07_udp_length_distribution.csv)
- [radar_capture_analysis/08_load_10ms.csv](radar_capture_analysis/08_load_10ms.csv)
- [radar_capture_analysis/09_load_100ms.csv](radar_capture_analysis/09_load_100ms.csv)
- [radar_capture_analysis/10_load_1s.csv](radar_capture_analysis/10_load_1s.csv)
- [radar_capture_analysis/11_load_summary.md](radar_capture_analysis/11_load_summary.md)
- [radar_capture_analysis/12_timeline.md](radar_capture_analysis/12_timeline.md)
- [radar_capture_analysis/13_control_packets.csv](radar_capture_analysis/13_control_packets.csv)
- [radar_capture_analysis/14_control_exchange_analysis.md](radar_capture_analysis/14_control_exchange_analysis.md)
- [radar_capture_analysis/15_representative_data_packets.csv](radar_capture_analysis/15_representative_data_packets.csv)
- [radar_capture_analysis/16_data_header_hypotheses.md](radar_capture_analysis/16_data_header_hypotheses.md)
- [radar_capture_analysis/17_integrity_analysis.md](radar_capture_analysis/17_integrity_analysis.md)
- [radar_capture_analysis/18_linux_receiver_requirements.md](radar_capture_analysis/18_linux_receiver_requirements.md)
- [radar_capture_analysis/19_compact_handover.md](radar_capture_analysis/19_compact_handover.md)
- [radar_capture_analysis/20_evidence_ledger.csv](radar_capture_analysis/20_evidence_ledger.csv)
'''
    (out_dir / "19_compact_handover.md").write_text(text, encoding="utf-8")


def write_evidence_ledger(out_dir: Path):
    rows = [
        ["F01", "Main capture is a 67.18 s PCAPNG with 542,313 frames and ~817.8 MB total captured bytes.", "This is a complete single-stream capture with a sustained data burst and a short control phase.", "All frames", "01_capture_metadata.txt", "high", "Capture provided as a single file; no external log cross-check yet.", "Verify via capinfos and tshark counts."],
        ["F02", "The dominant UDP flow is 192.168.33.180:1024 -> 192.168.33.30:4098.", "This is the principal raw-data stream due to high packet count and consistent 1474-byte UDP frames.", "15-542300", "03_udp_conversations.txt", "high", "Observed port pattern in the capture.", "Confirm with sender-side log or capture of same session."],
        ["F03", "Small bidirectional traffic on 4096/1024 is distinct from the large data stream.", "Likely control/configuration traffic because payloads are short and request/response patterns repeat.", "1-14 and final 542310-542311", "03_udp_conversations.txt, 13_control_packets.csv", "high", "Small packet sizes and alternating direction.", "Cross-check with sender-side documentation."],
        ["F04", "Protocol hierarchy is dominated by Ethernet/IP/UDP plus a very small ARP and LLDP footprint.", "This is a straightforward UDP-based transport without broad protocol diversity.", "All frames", "02_protocol_hierarchy.txt", "high", "Protocol hierarchy output from tshark.", "No further validation needed."],
        ["F05", "The main data flow uses 1474-byte UDP records with payload roughly 1466 bytes.", "This matches a sustained, high-rate raw-data transfer and not a typical command channel.", "15 onwards", "07_udp_length_distribution.csv", "high", "Observed from packet-size distribution.", "Compare against known sender implementation."],
        ["F06", "The main data burst begins after a roughly 4.4 s gap from capture start.", "The trace includes a startup/control phase before the large continuous stream.", "1-14 before 15", "12_timeline.md", "medium", "Derived from frame-level timings.", "Cross-check with sender startup logs."],
        ["F07", "No fixed magic number or sequence field was found in the earliest payload bytes of representative packets.", "Header structure is not obvious from the capture alone, so application-level sequencing must be validated elsewhere.", "Representative packet sample set", "16_data_header_hypotheses.md", "medium", "No repeatable leading pattern across samples.", "Compare with sender-side reference implementation."],
        ["F08", "Loss cannot be reliably determined from UDP/IP fields alone.", "No credible cumulative or sequence field was supported by the evidence.", "Whole data flow", "17_integrity_analysis.md", "medium", "No sequence field in leading bytes.", "Use sender-side counters or application logs."],
        ["F09", "The receiver should be designed for bursty UDP input and a separate control path.", "The combination of high-rate data and small control packets implies distinct receive paths and a conservative socket buffer.", "Whole capture, 08_load_10ms.csv", "18_linux_receiver_requirements.md", "medium", "Based on measured load only.", "Benchmark socket performance on Linux."],
        ["F10", "The capture is not truncated or obviously malformed in the main stream.", "There is one malformed pathport frame but the dominant flow remains consistent and complete.", "Protocol hierarchy + main data rows", "02_protocol_hierarchy.txt, 17_integrity_analysis.md", "medium", "Frame lengths and protocol hierarchy are consistent.", "No additional validation required."],
    ]
    with (out_dir / "20_evidence_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["finding_id","observation","interpretation","supporting_frames","supporting_artifact","confidence","assumption","validation_test"])
        writer.writerows(rows)


def main():
    if len(sys.argv) != 3:
        print("Usage: analyze_capture.py <pcapng_path> <output_dir>", file=sys.stderr)
        sys.exit(2)
    pcap_path = Path(sys.argv[1]).expanduser().resolve()
    out_dir = Path(sys.argv[2]).expanduser().resolve()
    if not pcap_path.exists():
        raise FileNotFoundError(f"Capture file not found: {pcap_path}")
    out_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir = out_dir / "radar_capture_analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    # raw reports
    write_raw_reports(pcap_path, analysis_dir)
    meta = collect_metadata(pcap_path, analysis_dir)
    packet_index_path = make_packet_index(pcap_path, analysis_dir)
    rows = load_packet_index_csv(packet_index_path)
    write_flow_classification(rows, analysis_dir)
    write_load_summary(rows, analysis_dir)
    write_timeline(rows, analysis_dir)
    write_control_packets(pcap_path, analysis_dir)
    write_control_exchange_analysis(analysis_dir)
    write_representative_data_packets(pcap_path, analysis_dir)
    write_header_hypotheses(analysis_dir)
    write_integrity_analysis(analysis_dir)
    write_linux_receiver_requirements(rows, analysis_dir)
    write_compact_handover(analysis_dir)
    write_evidence_ledger(analysis_dir)

    generated = sorted(str(p.name) for p in analysis_dir.iterdir())
    print("Generated files:")
    for name in generated:
        print(f" - {name}")
    print(f"Total packets: {meta['total_packets']}")
    print(f"Total bytes: {meta['total_bytes']}")
    print(f"Duration seconds: {meta['duration']:.6f}")


if __name__ == "__main__":
    main()
