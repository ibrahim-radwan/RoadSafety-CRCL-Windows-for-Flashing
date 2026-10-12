from processing.radar_config import parse_cfg_file, parse_calibration
from processing.streaming import run_live
from pathlib import Path

cfg  = parse_cfg_file("config/build_shortrange_inf/cascade_shortrange.cfg")
corr = parse_calibration("config/build_shortrange_inf/cascade_shortrange.cfg",
                         cfg.num_tx, cfg.num_rx)

run_live(cfg, corr,
         frame_folder=Path("capture/frames"),
         loop=False,
         quiet=False)