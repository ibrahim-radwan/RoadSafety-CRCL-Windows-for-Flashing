## Compact Summary

### What changed
- Disabled live streaming disk writes by default.
- Added explicit `--record` flag to enable saving `frame_*.bin`.
- Updated `FileMonitor` so it can stream frames from memory when `out_dir=None`.
- Changed streaming callback to accept bytes directly, avoiding file reads.
- Preserved existing offline/record workflows.
- Fixed a crash in `clean_capture_artifacts()` when `out_dir` is `None`.

### Files updated
- dca.py
- streaming.py
- live_capture.py