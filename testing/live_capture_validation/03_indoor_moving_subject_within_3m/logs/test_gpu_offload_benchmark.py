from processing.radar_config import parse_cfg_file
from processing.gpu_accel import benchmark
cfg = parse_cfg_file("config/build_shortrange_inf/cascade_shortrange.cfg")
benchmark(cfg, n_trials=10)