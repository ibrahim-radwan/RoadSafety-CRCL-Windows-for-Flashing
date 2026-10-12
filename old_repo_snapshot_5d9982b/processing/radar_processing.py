"""
radar_processing.py  —  AWR2243-2X cascade DSP pipeline
========================================================
Stages
  1.  Calibration (phase + amplitude)
  2.  Range FFT (windowed)
  3.  MTI clutter removal (slow-time mean subtraction)
  4.  Virtual-array formation
  5.  Doppler FFT (windowed, fftshifted) + zero-Doppler notch
  6.  Range-Doppler maps (dB, VA-averaged)
  7.  2-D K-Radar CA-CFAR + NMS on RD map
  8.  Azimuth beamforming (FFT / Capon / MUSIC / Bartlett)
  9.  2-D CFAR + NMS on RA map
  10. Elevation FFT
  11. arrDREA [N_range, N_el, N_az]
  12. xyz point cloud from RA detections
  13. Optional auto-save of arrDREA / xyz
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

import numpy as np
import numpy.linalg as LA
from scipy.ndimage import convolve as ndconvolve, maximum_filter, gaussian_filter
from scipy.signal import windows as swin

from .radar_config import RadarConfig, C


# ============================================================================
# Result container
# ============================================================================

@dataclass
class ProcessingResult:
    RD_raw:   Optional[np.ndarray] = None   # [N_dop, N_range]  dB
    RD_mti:   Optional[np.ndarray] = None   # [N_dop, N_range]  dB  (after MTI+notch)
    RA:       Optional[np.ndarray] = None   # [N_range, N_az]   dB
    RE:       Optional[np.ndarray] = None   # [N_range, N_el]   dB
    rd_det:   Optional[np.ndarray] = None   # [N_dop, N_range]  bool
    ra_det:   Optional[np.ndarray] = None   # [N_range, N_az]   bool
    rd_thresh:Optional[np.ndarray] = None
    ra_thresh:Optional[np.ndarray] = None
    arr_drea: Optional[np.ndarray] = None   # [N_range, N_el, N_az]
    xyz_cloud:Optional[np.ndarray] = None   # [N, 7]: x,y,z,pwr,dop,rng,az
    range_axis:   Optional[np.ndarray] = None
    doppler_axis: Optional[np.ndarray] = None
    az_axis:      Optional[np.ndarray] = None   # degrees
    el_axis:      Optional[np.ndarray] = None   # degrees
    aoa_method: str = "fft"


# ============================================================================
# Helpers
# ============================================================================

def _win(name: str, n: int, atten: float = 60.0) -> np.ndarray:
    name = name.lower()
    if name in ("none", "rect"):           return np.ones(n, np.float32)
    if name in ("hann", "hanning"):        return swin.hann(n).astype(np.float32)
    if name == "hamming":                  return swin.hamming(n).astype(np.float32)
    if name == "blackman":                 return swin.blackman(n).astype(np.float32)
    if name in ("chebyshev", "chebwin"):   return swin.chebwin(n, atten).astype(np.float32)
    return np.ones(n, np.float32)


def _db(x: np.ndarray, ref: float = 1e-9) -> np.ndarray:
    return (20.0 * np.log10(np.abs(x) + ref)).astype(np.float32)


def _power_db_reduce(x: np.ndarray, axis=-1, ref: float = 1e-12) -> np.ndarray:
    """
    Convert complex data to dB after averaging power along the chosen axis.

    Using mean power is more stable than averaging magnitudes directly,
    especially for RD/RA/RE maps used by CFAR.
    """
    pwr = np.mean(np.abs(x) ** 2, axis=axis)
    return (10.0 * np.log10(np.maximum(pwr, ref))).astype(np.float32)


def _range_keep_mask(cfg: RadarConfig, n_range: int) -> np.ndarray:
    r_ax = cfg.range_axis[:n_range]
    r_max = cfg.max_range_m if cfg.max_range_m > 0 else float(r_ax[-1])
    return ((r_ax >= cfg.min_range_m) & (r_ax <= r_max)).astype(bool)


def _prune_rd_sidelobes(rd_det: np.ndarray, RD_mti: np.ndarray,
                        cfg: RadarConfig) -> np.ndarray:
    if (not getattr(cfg, "apply_sidelobe_filters", False)) or rd_det.sum() == 0:
        return rd_det
    keep = rd_det.copy()
    rel_db = float(getattr(cfg, "rd_sidelobe_db", 0.0))
    if rel_db <= 0:
        return keep
    col_max = np.max(RD_mti, axis=0, keepdims=True)
    keep &= RD_mti >= (col_max - rel_db)
    return keep


def _prune_ra_sidelobes(ra_det: np.ndarray, RA: np.ndarray,
                        cfg: RadarConfig) -> np.ndarray:
    if (not getattr(cfg, "apply_sidelobe_filters", False)) or ra_det.sum() == 0:
        return ra_det
    keep = ra_det.copy()
    rel_db = float(getattr(cfg, "ra_sidelobe_db", 0.0))
    if rel_db <= 0:
        return keep
    row_max = np.max(RA, axis=1, keepdims=True)
    keep &= RA >= (row_max - rel_db)
    return keep


def _within_roi(val: float, bounds) -> bool:
    return bounds is None or (float(bounds[0]) <= val <= float(bounds[1]))


def _suppress_doppler_stripes(rd_map: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    if (not getattr(cfg, "doppler_stripe_removal", False)) or rd_map.size == 0:
        return rd_map
    baseline = np.median(rd_map, axis=1, keepdims=True)
    global_ref = float(np.median(baseline))
    return (rd_map - baseline + global_ref).astype(np.float32)


def _ra_focus_mask_from_rd(RD_mti: np.ndarray, rd_det: Optional[np.ndarray],
                           cfg: RadarConfig) -> np.ndarray:
    """
    Build a per-range Doppler selection mask for cleaner RA formation.

    We prefer RD-confirmed Doppler bins. If CFAR produced no bins in a range,
    we fall back to the strongest Doppler bins for that range so RA does not
    collapse into noise or vanish entirely.
    """
    n_dop, n_r = RD_mti.shape
    mask = np.zeros((n_dop, n_r), dtype=bool)
    expand = 1

    for ri in range(n_r):
        idx = np.empty(0, dtype=int)
        if rd_det is not None and ri < rd_det.shape[1]:
            idx = np.flatnonzero(rd_det[:, ri])

        if idx.size == 0:
            col = RD_mti[:, ri].astype(np.float32)
            finite = np.isfinite(col)
            if not finite.any():
                continue
            valid_idx = np.flatnonzero(finite)
            vals = col[valid_idx]
            med = float(np.median(vals))
            peak = float(np.max(vals))
            thr = max(med + 6.0, peak - 8.0)
            idx = valid_idx[vals >= thr]
            if idx.size == 0:
                top_k = min(3, valid_idx.size)
                idx = valid_idx[np.argsort(vals)[-top_k:]]

        for di in idx:
            lo = max(0, int(di) - expand)
            hi = min(n_dop, int(di) + expand + 1)
            mask[lo:hi, ri] = True

    return mask


def _collapse_ra_from_fft(az_cube: np.ndarray, RD_mti: np.ndarray,
                          rd_det: Optional[np.ndarray],
                          cfg: RadarConfig) -> np.ndarray:
    """
    Collapse [dop, range, az] into a cleaner [range, az] RA map using only
    RD-relevant Doppler bins for each range.
    """
    pwr = np.abs(az_cube) ** 2
    focus = _ra_focus_mask_from_rd(RD_mti, rd_det, cfg)
    n_dop, n_r, _ = pwr.shape
    ra = np.zeros((n_r, pwr.shape[-1]), dtype=np.float32)
    for ri in range(n_r):
        sel = focus[:, ri]
        if np.any(sel):
            row_pwr = np.mean(pwr[sel, ri, :], axis=0)
        else:
            row_pwr = np.mean(pwr[:, ri, :], axis=0)
        ra[ri] = 10.0 * np.log10(np.maximum(row_pwr, 1e-12))
    return ra.astype(np.float32)


def _range_snapshots(virt_rd: np.ndarray, focus_mask: Optional[np.ndarray], ri: int) -> np.ndarray:
    """
    Return [N_snap, N_va] snapshots for one range bin, optionally restricted
    to the RD-focused Doppler bins selected for that range.
    """
    snaps = virt_rd[:, ri, :]
    if focus_mask is not None and ri < focus_mask.shape[1]:
        sel = focus_mask[:, ri]
        if np.any(sel):
            snaps = snaps[sel, :]
    return np.asarray(snaps, dtype=np.complex64)


def _restrict_ra_candidates(ra_det: np.ndarray, RA: np.ndarray, RE: Optional[np.ndarray],
                            cfg: RadarConfig) -> np.ndarray:
    if (not getattr(cfg, "strict_object_filtering", False)) or ra_det.sum() == 0:
        return ra_det
    keep = np.zeros_like(ra_det, dtype=bool)
    max_per_range = max(int(getattr(cfg, "max_az_detections_per_range", 1)), 1)
    ra_prom = float(getattr(cfg, "ra_peak_prominence_db", 0.0))
    el_prom = float(getattr(cfg, "el_peak_prominence_db", 0.0))

    for ri in np.where(ra_det.any(axis=1))[0]:
        row_det = np.flatnonzero(ra_det[ri])
        if row_det.size == 0:
            continue
        row = RA[ri]
        row_median = float(np.median(row[np.isfinite(row)])) if np.isfinite(row).any() else float("-inf")
        peak_candidates = []
        for ai in row_det:
            left = max(ai - 1, 0)
            right = min(ai + 2, row.shape[0])
            local_peak = float(np.max(row[left:right]))
            if row[ai] < (local_peak - 0.05):
                continue
            if ra_prom > 0.0 and (row[ai] - row_median) < ra_prom:
                continue
            peak_candidates.append(ai)
        if not peak_candidates:
            continue
        if RE is not None and ri < RE.shape[0] and el_prom > 0.0:
            re_row = RE[ri]
            re_med = float(np.median(re_row[np.isfinite(re_row)])) if np.isfinite(re_row).any() else float("-inf")
            if (float(np.max(re_row)) - re_med) < el_prom:
                continue
        peak_candidates = np.array(peak_candidates, dtype=int)
        order = np.argsort(row[peak_candidates])[::-1][:max_per_range]
        keep[ri, peak_candidates[order]] = True
    return keep


def _collapse_virtual_channels(virt_rd: np.ndarray, az_positions: np.ndarray
                               ) -> Tuple[np.ndarray, np.ndarray]:
    pos = np.asarray(az_positions, dtype=np.float32).reshape(-1)
    if virt_rd.shape[-1] != pos.size or pos.size == 0:
        return virt_rd, pos
    uniq, inv = np.unique(pos, return_inverse=True)
    if uniq.size == pos.size:
        return virt_rd, pos
    collapsed = np.zeros(virt_rd.shape[:-1] + (uniq.size,), dtype=np.complex64)
    counts = np.bincount(inv, minlength=uniq.size).astype(np.float32)
    for src_idx, dst_idx in enumerate(inv):
        collapsed[..., dst_idx] += virt_rd[..., src_idx]
    collapsed /= np.maximum(counts, 1.0)[np.newaxis, np.newaxis, :]
    return collapsed, uniq.astype(np.float32)


def _elevation_pair_indices(ch_az: list, ch_el: list) -> Tuple[np.ndarray, np.ndarray]:
    """
    Match top-row elevation channels to bottom-row azimuth channels that share
    the same azimuth position.
    """
    pos_to_bottom = {}
    for idx, ch in enumerate(ch_az):
        pos_to_bottom.setdefault(int(ch["az"]), idx)

    bot_idx = []
    top_idx = []
    for ei, ch in enumerate(ch_el):
        pos = int(ch["az"])
        if pos in pos_to_bottom:
            bot_idx.append(int(pos_to_bottom[pos]))
            top_idx.append(int(ei))
    return np.asarray(bot_idx, dtype=int), np.asarray(top_idx, dtype=int)


def _covariance_from_snapshots(X: np.ndarray, diag_load: float = 0.0,
                               fb_avg: bool = False) -> np.ndarray:
    n_ch, n_snap = X.shape
    Rxx = (X @ X.conj().T) / max(int(n_snap), 1)
    Rxx = 0.5 * (Rxx + Rxx.conj().T)
    if fb_avg and n_ch > 1:
        J = np.fliplr(np.eye(n_ch, dtype=np.float32)).astype(np.complex64)
        Rxx = 0.5 * (Rxx + J @ Rxx.conj() @ J)
    load = float(diag_load)
    if load > 0.0:
        tr = float(np.trace(Rxx).real)
        scale = tr / max(n_ch, 1) if tr > 0.0 else 1.0
        Rxx = Rxx + np.eye(n_ch, dtype=np.complex64) * (load * scale)
    return Rxx.astype(np.complex64)


# ============================================================================
# Stage 1 – Calibration
# ============================================================================

def apply_calibration(cube: np.ndarray, corr: np.ndarray) -> np.ndarray:
    """cube [TX,loops,RX,N]  corr [TX,RX]  → corrected cube"""
    return (cube * corr[:, np.newaxis, :, np.newaxis]).astype(np.complex64)


# ============================================================================
# Stage 2 – Range FFT
# ============================================================================

def range_fft(cube: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    n   = cfg.range_fft_size or cube.shape[-1]
    win = _win(cfg.range_window, cube.shape[-1], cfg.chebyshev_atten_db)
    return np.fft.fft(cube * win[np.newaxis, np.newaxis, np.newaxis, :],
                      n=n, axis=-1).astype(np.complex64)


# ============================================================================
# Stage 3+4 – MTI + Virtual arrays
# ============================================================================

def form_virtual_arrays(range_cube: np.ndarray, cfg: RadarConfig,
                        ch_az: list, ch_el: list):
    """
    Returns:
      virt_az [loops, range, N_va_az]
      virt_el [loops, range, N_va_el]
    """
    virt_az = np.stack([range_cube[c["tx"], :, c["rx"], :] for c in ch_az],
                       axis=-1).astype(np.complex64)
    virt_el = np.stack([range_cube[c["tx"], :, c["rx"], :] for c in ch_el],
                       axis=-1).astype(np.complex64)
    return virt_az, virt_el


# ============================================================================
# Stage 5 – Doppler FFT + zero-Doppler notch
# ============================================================================

def doppler_fft(virt: np.ndarray, cfg: RadarConfig,
                remove_clutter: bool = False,
                use_window: bool = True) -> np.ndarray:
    """[loops, range, VA] → [dop, range, VA]"""
    x = np.asarray(virt, dtype=np.complex64)
    if remove_clutter:
        x = x - x.mean(axis=0, keepdims=True)
    if use_window:
        w = _win(cfg.doppler_window, cfg.num_loops, cfg.chebyshev_atten_db)
        x = x * w[:, np.newaxis, np.newaxis]
    n = cfg.doppler_fft_size or cfg.num_loops
    return np.fft.fftshift(np.fft.fft(x, n=n, axis=0), axes=0).astype(np.complex64)


def zero_dc_notch(arr: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    n = cfg.zero_dc_bins
    if n <= 0:
        return arr
    mid = arr.shape[0] // 2
    out = arr.copy()
    out[max(0, mid-n):min(arr.shape[0], mid+n+1)] = 0.0
    return out


# ============================================================================
# Stage 6 – Azimuth beamforming
# ============================================================================

def _az_fft(virt_rd: np.ndarray, cfg: RadarConfig) -> np.ndarray:
    n_va = virt_rd.shape[-1]
    w    = _win(cfg.az_window, n_va, cfg.chebyshev_atten_db)
    return np.fft.fftshift(
        np.fft.fft(virt_rd * w[np.newaxis, np.newaxis, :], n=cfg.az_fft_size, axis=-1),
        axes=-1).astype(np.complex64)


def _az_window_weights(cfg: RadarConfig, n_va: int) -> np.ndarray:
    return _win(cfg.az_window, n_va, cfg.chebyshev_atten_db).astype(np.float32)


def _steering_matrix(az_positions: np.ndarray, az_fft_size: int) -> np.ndarray:
    """
    Build steering matrix for the virtual aperture using ACTUAL positions.

    az_positions : 1-D array of aperture positions in λ/2 units
                   (from ch_az sorted list — NOT simple arange).
    Returns sv [n_az_bins, N_va]  complex64
    """
    sin_v = np.linspace(-1.0, 1.0, az_fft_size, endpoint=False)
    # d/λ = 0.5 for λ/2 spacing → phase per bin: 2π × (d/λ) × sin = π × pos × sin
    return np.exp(1j * np.pi * np.outer(sin_v, az_positions)).astype(np.complex64)


def _az_capon(virt_rd: np.ndarray, cfg: RadarConfig,
              az_positions: np.ndarray,
              focus_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Capon (MVDR) beamformer using actual aperture positions.

    az_positions : physical aperture positions in λ/2 units for each virtual channel
    virt_rd      : [N_dop, N_range, N_va]
    Returns      : [N_range, az_fft_size]  dB
    """
    n_dop, n_r, n_va = virt_rd.shape
    n  = cfg.az_fft_size
    taper = _az_window_weights(cfg, n_va)
    sv = (_steering_matrix(az_positions, n) * taper[np.newaxis, :]).astype(np.complex64)   # [n, N_va]
    ra = np.zeros((n_r, n), dtype=np.float32)
    for ri in range(n_r):
        Xr  = _range_snapshots(virt_rd, focus_mask, ri)
        X   = (Xr.T * taper[:, np.newaxis]).astype(np.complex64)   # [N_va, N_snap]
        Rxx = _covariance_from_snapshots(
            X,
            diag_load=max(float(getattr(cfg, "music_diag_load", 0.0)), 1e-6),
            fb_avg=bool(getattr(cfg, "music_forward_backward_avg", False)),
        )
        try:    Ri = LA.inv(Rxx)
        except: Ri = LA.pinv(Rxx)
        # P_capon(k) = 1 / (sv[k]^H R^-1 sv[k])
        denom  = np.einsum("ki,ij,kj->k", sv.conj(), Ri, sv).real
        ra[ri] = 20.0 * np.log10(np.reciprocal(np.maximum(denom, 1e-20)) + 1e-9)
    return ra


def _az_music(virt_rd: np.ndarray, cfg: RadarConfig,
              az_positions: np.ndarray,
              focus_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    MUSIC pseudo-spectrum using actual aperture positions.

    Returns [N_range, az_fft_size]  dB
    """
    n_dop, n_r, n_va = virt_rd.shape
    n  = cfg.az_fft_size
    max_sources = max(min(n_va, n_dop) - 1, 1)
    ns = int(np.clip(cfg.music_num_sources, 1, max_sources))
    # sv [N_va, n] — column per azimuth bin
    taper = _az_window_weights(cfg, n_va)
    sv = (_steering_matrix(az_positions, n).T * taper[:, np.newaxis]).astype(np.complex64)   # [N_va, n]
    ra = np.zeros((n_r, n), dtype=np.float32)
    for ri in range(n_r):
        Xr   = _range_snapshots(virt_rd, focus_mask, ri)
        X    = (Xr.T * taper[:, np.newaxis]).astype(np.complex64)
        Rxx  = _covariance_from_snapshots(
            X,
            diag_load=float(getattr(cfg, "music_diag_load", 0.0)),
            fb_avg=bool(getattr(cfg, "music_forward_backward_avg", False)),
        )
        try:
            _, V = LA.eigh(Rxx)
        except LA.LinAlgError:
            Rxx = _covariance_from_snapshots(
                X,
                diag_load=max(float(getattr(cfg, "music_diag_load", 0.0)), 1e-3),
                fb_avg=False,
            )
            _, V = LA.eigh(Rxx)
        En   = V[:, :max(n_va - ns, 1)]    # noise subspace [N_va, N_va-ns]
        # P_MUSIC(k) = 1 / ||En^H sv_k||^2
        proj  = En.conj().T @ sv   # [N_va-ns, n]
        denom = np.sum(np.abs(proj)**2, axis=0)
        ra[ri] = 20.0 * np.log10(np.reciprocal(np.maximum(denom, 1e-20)) + 1e-9)
    return ra


def _az_bartlett(virt_rd: np.ndarray, cfg: RadarConfig,
                 az_positions: np.ndarray,
                 focus_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Bartlett (conventional / matched-filter) beamformer using actual positions.

    Returns [N_range, az_fft_size]  dB
    """
    n_dop, n_r, n_va = virt_rd.shape
    n  = cfg.az_fft_size
    taper = _az_window_weights(cfg, n_va)
    sv = (_steering_matrix(az_positions, n) * taper[np.newaxis, :]).astype(np.complex64)   # [n, N_va]
    ra = np.zeros((n_r, n), dtype=np.float32)
    for ri in range(n_r):
        Xr  = _range_snapshots(virt_rd, focus_mask, ri)
        X   = (Xr.T * taper[:, np.newaxis]).astype(np.complex64)
        Rxx = _covariance_from_snapshots(
            X,
            diag_load=0.0,
            fb_avg=bool(getattr(cfg, "music_forward_backward_avg", False)),
        )
        # P_Bartlett(k) = sv[k]^H R sv[k]
        spec = np.einsum("ik,ij,jk->k", sv.conj(), Rxx, sv).real
        ra[ri] = 20.0 * np.log10(np.maximum(spec, 1e-20) + 1e-9)
    return ra


# ============================================================================
# Stage 7 – K-Radar CA-CFAR + NMS
# ============================================================================

def cfar_2d(heatmap: np.ndarray, cfg: RadarConfig
            ) -> Tuple[np.ndarray, np.ndarray]:
    heat = heatmap.astype(np.float32, copy=False)
    g, t = cfg.cfar_guard, cfg.cfar_train
    msz  = (2*(g[0]+t[0])+1, 2*(g[1]+t[1])+1)
    mask = np.ones(msz, dtype=np.float32)
    mask[t[0]:t[0]+2*g[0]+1, t[1]:t[1]+2*g[1]+1] = 0.0
    n_tc = int(np.count_nonzero(mask))
    mode = str(getattr(cfg, "cfar_method", "ca")).lower()

    if mode == "os":
        fill = float(np.nanmin(heat)) if np.isfinite(heat).any() else 0.0
        padded = np.pad(heat,
                        ((t[0] + g[0], t[0] + g[0]),
                         (t[1] + g[1], t[1] + g[1])),
                        mode="constant", constant_values=fill)
        win = np.lib.stride_tricks.sliding_window_view(padded, msz)
        train_cells = win[..., mask.astype(bool)]
        train_cells.sort(axis=-1)
        rank = int(np.clip(np.ceil(float(cfg.cfar_os_rank) * n_tc) - 1, 0, n_tc - 1))
        noise = train_cells[..., rank]
        alpha = n_tc * (cfg.cfar_fa_rate ** (-1.0 / max(n_tc, 1)) - 1.0)
        thresh = alpha * noise
    else:
        left_mask = mask.copy()
        right_mask = mask.copy()
        split_col = t[1] + g[1]
        left_mask[:, split_col + 1:] = 0.0
        right_mask[:, :split_col] = 0.0

        full_noise = ndconvolve(heat, mask / max(float(n_tc), 1.0), mode='mirror')
        if mode in ("caso", "cago"):
            n_left = float(np.count_nonzero(left_mask)) or 1.0
            n_right = float(np.count_nonzero(right_mask)) or 1.0
            left_noise = ndconvolve(heat, left_mask / n_left, mode='mirror')
            right_noise = ndconvolve(heat, right_mask / n_right, mode='mirror')
            if mode == "caso":
                noise = np.minimum(left_noise, right_noise)
            else:
                noise = np.maximum(left_noise, right_noise)
            alpha_cells = max(min(n_left, n_right), 1.0)
        else:
            noise = full_noise
            alpha_cells = float(n_tc) or 1.0
        alpha = alpha_cells * (cfg.cfar_fa_rate ** (-1.0 / alpha_cells) - 1.0)
        thresh = alpha * noise

    det = heat > thresh
    if cfg.cfar_margin_db > 0:
        det = det & ((heat - thresh) >= cfg.cfar_margin_db)
    if getattr(cfg, "cfar_min_power_db", 0.0) > 0:
        det = det & (heat >= float(cfg.cfar_min_power_db))
    nk  = tuple(max(1, k) for k in cfg.nms_size)
    lmx = maximum_filter(heat, size=nk, mode='nearest')
    det = det & (heat >= lmx - 0.05)
    return det, thresh.astype(np.float32)


# ============================================================================
# Stage 8 – Elevation FFT
# ============================================================================

def elevation_fft(virt_el_top_rd: np.ndarray,
                  virt_el_bot_rd: np.ndarray,
                  cfg: RadarConfig) -> np.ndarray:
    """
    Elevation response for the two-row cascade array using matched top/bottom
    azimuth positions.

    For each candidate elevation angle, we phase-compensate the top-row channel
    against its bottom-row counterpart and sum coherently across matched pairs.
    """
    if virt_el_top_rd.size == 0 or virt_el_bot_rd.size == 0:
        return np.zeros((virt_el_top_rd.shape[1], cfg.el_fft_size), dtype=np.float32)

    sin_el = np.linspace(
        -min(1.0 / (2.0 * cfg.d_el_lambda), 1.0),
        min(1.0 / (2.0 * cfg.d_el_lambda), 1.0),
        cfg.el_fft_size,
        endpoint=False,
        dtype=np.float32,
    )
    steer = np.exp(-1j * 2.0 * np.pi * cfg.d_el_lambda * sin_el).astype(np.complex64)

    top = np.asarray(virt_el_top_rd, dtype=np.complex64)
    bot = np.asarray(virt_el_bot_rd, dtype=np.complex64)
    if top.shape != bot.shape:
        n_pairs = min(top.shape[-1], bot.shape[-1])
        top = top[..., :n_pairs]
        bot = bot[..., :n_pairs]

    w = _win(cfg.el_window, top.shape[-1], cfg.chebyshev_atten_db)
    top = top * w[np.newaxis, np.newaxis, :]
    bot = bot * w[np.newaxis, np.newaxis, :]

    resp = np.empty((top.shape[1], cfg.el_fft_size), dtype=np.float32)
    for ei, ph in enumerate(steer):
        comb = bot + top * ph
        resp[:, ei] = 10.0 * np.log10(
            np.maximum(np.mean(np.abs(comb) ** 2, axis=(0, 2)), 1e-12)
        )
    return resp.astype(np.float32)


# ============================================================================
# Stage 9 – arrDREA
# ============================================================================

def build_arr_drea(az_cube: np.ndarray, el_data: np.ndarray,
                   cfg: RadarConfig) -> np.ndarray:
    az_pow = (np.abs(az_cube) ** 2).sum(axis=0)   # [N_range, N_az]
    if np.iscomplexobj(el_data):
        el_pow = (np.abs(el_data) ** 2).sum(axis=0)
    else:
        el_pow = np.power(10.0, np.asarray(el_data, dtype=np.float32) / 10.0)
    return (el_pow[:, :, np.newaxis] * az_pow[:, np.newaxis, :]).astype(np.float32)


# ============================================================================
# Stage 10 – xyz point cloud
# ============================================================================

def extract_xyz(ra_det: np.ndarray, RA: np.ndarray, RE: np.ndarray,
                doppler_axis: np.ndarray, RD_mti: np.ndarray,
                rd_det: Optional[np.ndarray],
                cfg: RadarConfig, max_pts: Optional[int] = None) -> np.ndarray:
    r_ax  = cfg.range_axis
    az_ax = cfg.az_axis_deg
    el_ax = cfg.el_axis_deg
    dop_thr = cfg.min_abs_doppler_mps if cfg.min_abs_doppler_mps > 0 else 0.5 * cfg.dop_res

    ri_idx, ai_idx = np.where(ra_det)
    if ri_idx.size == 0:
        return np.empty((0, 7), dtype=np.float32)

    max_pts = int(max_pts if max_pts is not None else getattr(cfg, "point_cloud_max_points", 12000))
    if ri_idx.size > max_pts:
        keep   = np.argpartition(RA[ri_idx, ai_idx], -max_pts)[-max_pts:]
        ri_idx, ai_idx = ri_idx[keep], ai_idx[keep]

    r_max = cfg.max_range_m if cfg.max_range_m > 0 else float(r_ax[-1])
    records = []
    for ri, ai in zip(ri_idx, ai_idx):
        if ri >= len(r_ax): continue
        rng = float(r_ax[ri])
        if rng < cfg.min_range_m or rng > r_max: continue
        az_deg = float(az_ax[min(ai, len(az_ax)-1)])
        pwr    = float(RA[ri, ai])

        # Elevation from RE peak
        el_deg = 0.0
        if RE is not None and ri < RE.shape[0]:
            ei     = int(np.argmax(RE[ri]))
            el_deg = float(el_ax[min(ei, len(el_ax)-1)])

        # Doppler: highest-power moving bin
        dop = 0.0
        if RD_mti is not None and ri < RD_mti.shape[1] and len(doppler_axis) > 0:
            mov = np.abs(doppler_axis) >= dop_thr
            det_mask = None
            if rd_det is not None and ri < rd_det.shape[1]:
                det_mask = rd_det[:, ri].astype(bool)
                if mov.any():
                    det_mask = det_mask & mov
                if det_mask.any():
                    col = RD_mti[:, ri].copy()
                    col[~det_mask] = -np.inf
                    if np.isfinite(col).any():
                        dop = float(doppler_axis[int(np.argmax(col))])
            if dop == 0.0 and mov.any():
                col = RD_mti[:, ri].copy()
                col[~mov] = -np.inf
                if np.isfinite(col).any():
                    dop = float(doppler_axis[int(np.argmax(col))])

        az_r  = np.deg2rad(az_deg); el_r = np.deg2rad(el_deg)
        ce    = np.cos(el_r)
        x = float(rng * ce * np.sin(az_r))
        y = float(rng * ce * np.cos(az_r))
        z = float(rng * np.sin(el_r))
        if not (_within_roi(x, getattr(cfg, "roi_x_m", None)) and
                _within_roi(y, getattr(cfg, "roi_y_m", None)) and
                _within_roi(z, getattr(cfg, "roi_z_m", None))):
            continue
        records.append([x, y, z, pwr, dop, rng, az_deg])

    if not records:
        return np.empty((0, 7), np.float32)
    xyz = np.array(records, dtype=np.float32)
    order = np.argsort(xyz[:, 3])[::-1]
    return xyz[order]


# ============================================================================
# Save helpers
# ============================================================================

def save_arr_drea(arr: np.ndarray, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    np.save(path, arr)
    print(f"[SAVE] arrDREA {arr.shape} → {path}")


def save_xyz_cloud(xyz: np.ndarray, path: str):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    if path.lower().endswith(".csv"):
        np.savetxt(path, xyz, delimiter=",",
                   header="x_m,y_m,z_m,pwr_db,dop_mps,rng_m,az_deg", comments="")
    else:
        np.save(path, xyz)
    print(f"[SAVE] xyz_cloud {xyz.shape} → {path}")


# ============================================================================
# Main orchestrator
# ============================================================================

def process_frame(cube: np.ndarray, cfg: RadarConfig,
                  correction: Optional[np.ndarray] = None,
                  verbose: bool = True) -> ProcessingResult:
    res = ProcessingResult()
    res.range_axis   = cfg.range_axis
    res.doppler_axis = cfg.doppler_axis   # ±dop_max from waveform config
    res.az_axis      = cfg.az_axis_deg
    res.el_axis      = cfg.el_axis_deg
    res.aoa_method   = cfg.aoa_method
    N_r = cfg.n_range

    # 1. Calibration
    if correction is not None and cfg.apply_calibration:
        cube = apply_calibration(cube, correction)
        if verbose: print("[PROC] 1. Calibration applied")

    # 2. Range FFT
    range_cube = range_fft(cube, cfg)
    if verbose: print(f"[PROC] 2. Range FFT → {range_cube.shape}")

    # 3. Virtual arrays for cascaded radar
    ch_az, ch_el, _ = cfg.build_channel_table()
    va_az, va_el = form_virtual_arrays(range_cube, cfg, ch_az, ch_el)
    bot_idx, top_idx = _elevation_pair_indices(ch_az, ch_el)
    va_raw = va_az
    dop_win = True
    mti_dop = cfg.clutter_removal
    if verbose: print(f"[PROC] 3. VA az={va_az.shape} el={va_el.shape}")

    # 4. Doppler FFT
    rd_raw = doppler_fft(va_raw, cfg, remove_clutter=False,   use_window=dop_win)
    rd_mti = doppler_fft(va_az,  cfg, remove_clutter=mti_dop, use_window=dop_win)
    if bot_idx.size > 0 and top_idx.size > 0:
        rd_el_top = doppler_fft(va_el[:, :, top_idx], cfg, remove_clutter=mti_dop, use_window=dop_win)
        rd_el_bot = doppler_fft(va_az[:, :, bot_idx], cfg, remove_clutter=mti_dop, use_window=dop_win)
    else:
        rd_el_top = np.empty((cfg.doppler_fft_size or cfg.num_loops, N_r, 0), dtype=np.complex64)
        rd_el_bot = np.empty_like(rd_el_top)
    rd_mti = zero_dc_notch(rd_mti, cfg)
    rd_el_top = zero_dc_notch(rd_el_top, cfg)
    rd_el_bot = zero_dc_notch(rd_el_bot, cfg)
    if verbose: print(f"[PROC] 4. Doppler FFT → {rd_mti.shape}")

    # 5. RD maps (VA-averaged, dB)  — positive range half
    RD_raw = _power_db_reduce(rd_raw[:, :N_r, :], axis=-1)
    RD_mti = _power_db_reduce(rd_mti[:, :N_r, :], axis=-1)
    RD_raw = _suppress_doppler_stripes(RD_raw, cfg)
    RD_mti = _suppress_doppler_stripes(RD_mti, cfg)
    if cfg.gaussian_sigma > 0:
        RD_raw = gaussian_filter(RD_raw, cfg.gaussian_sigma).astype(np.float32)
        RD_mti = gaussian_filter(RD_mti, cfg.gaussian_sigma).astype(np.float32)
    res.RD_raw = RD_raw; res.RD_mti = RD_mti
    if verbose: print(f"[PROC] 5. RD maps → {RD_mti.shape}")

    # 6. CFAR on RD
    rd_det, rd_thresh = cfar_2d(RD_mti, cfg)
    rd_det = _prune_rd_sidelobes(rd_det, RD_mti, cfg)
    rd_det &= _range_keep_mask(cfg, RD_mti.shape[1])[np.newaxis, :]
    res.rd_det = rd_det; res.rd_thresh = rd_thresh
    if verbose: print(f"[PROC] 6. RD CFAR → {rd_det.sum()} detections")

    # 7. RA beamforming — pass ACTUAL aperture positions (fixes Capon/MUSIC)
    virt_pos   = rd_mti[:, :N_r, :]
    az_pos_arr = np.array([c["az"] for c in ch_az], dtype=np.float32)
    ra_focus_mask = _ra_focus_mask_from_rd(RD_mti, rd_det, cfg)
    if getattr(cfg, "music_use_unique_aperture", True):
        virt_pos, az_pos_arr = _collapse_virtual_channels(virt_pos, az_pos_arr)
    # az_pos_arr contains the real λ/2 positions, e.g. [0,1,...,7, 8,...,23, 23,...,37]

    if cfg.aoa_method == "capon":
        RA = _az_capon(virt_pos, cfg, az_pos_arr, ra_focus_mask)
    elif cfg.aoa_method == "music":
        RA = _az_music(virt_pos, cfg, az_pos_arr, ra_focus_mask)
    elif cfg.aoa_method == "bartlett":
        RA = _az_bartlett(virt_pos, cfg, az_pos_arr, ra_focus_mask)
    else:
        az_cube = _az_fft(virt_pos, cfg)
        RA = _collapse_ra_from_fft(az_cube, RD_mti, rd_det, cfg)[:N_r, :]
    if cfg.gaussian_sigma > 0:
        RA = gaussian_filter(RA, cfg.gaussian_sigma).astype(np.float32)
    res.RA = RA
    if verbose: print(f"[PROC] 7. RA map → {RA.shape}  ({cfg.aoa_method})")

    az_cube_drea = _az_fft(virt_pos, cfg) if cfg.aoa_method == "fft" else None

    # 8. CFAR on RA
    ra_det, ra_thresh = cfar_2d(RA, cfg)
    ra_det = _prune_ra_sidelobes(ra_det, RA, cfg)
    ra_det &= _range_keep_mask(cfg, RA.shape[0])[:, np.newaxis]
    if verbose: print(f"[PROC] 8. RA CFAR → {ra_det.sum()} detections")

    # 8b. High-reflection moving-object filter (optional)
    if getattr(cfg, 'filter_high_moving', False) and ra_det.sum() > 0:
        dop_thr = (cfg.high_moving_min_dop if cfg.high_moving_min_dop > 0
                   else 0.5 * cfg.dop_res)
        # Per-range-bin: True if moving energy exists
        mov_rows = np.abs(cfg.doppler_axis) >= dop_thr
        rd_moving = rd_det & mov_rows[:, np.newaxis]   # [N_dop, N_range]
        range_has_motion = rd_moving.any(axis=0)       # [N_range]

        # High-power gate: dB above local CFAR noise estimate
        db_thresh = cfg.high_moving_db_above
        high_power = (RA - ra_thresh) >= db_thresh      # [N_range, N_az]

        ra_det = ra_det & range_has_motion[:, np.newaxis] & high_power
        if verbose:
            print(f"[PROC] 8b. High-moving filter → {ra_det.sum()} detections")

    if cfg.moving_objects_only and ra_det.sum() > 0:
        dop_thr = (cfg.min_abs_doppler_mps if cfg.min_abs_doppler_mps > 0
                   else 0.5 * cfg.dop_res)
        mov_rows = np.abs(cfg.doppler_axis) >= dop_thr
        rd_moving = rd_det & mov_rows[:, np.newaxis]
        range_has_motion = rd_moving.any(axis=0)
        ra_det = ra_det & range_has_motion[:, np.newaxis]
        if verbose:
            print(f"[PROC] 8c. Moving-only gate → {ra_det.sum()} detections")

    if cfg.require_rd_confirmation and ra_det.sum() > 0 and rd_det.sum() > 0:
        dop_thr = (cfg.min_abs_doppler_mps if cfg.min_abs_doppler_mps > 0
                   else 0.5 * cfg.dop_res)
        if cfg.moving_objects_only:
            rd_confirm = rd_det & (np.abs(cfg.doppler_axis)[:, np.newaxis] >= dop_thr)
        else:
            rd_confirm = rd_det
        range_has_rd = rd_confirm.any(axis=0)
        ra_det = ra_det & range_has_rd[:, np.newaxis]
        if verbose:
            print(f"[PROC] 8d. RD confirmation → {ra_det.sum()} detections")

    # 9. Elevation
    RE = elevation_fft(rd_el_top[:, :N_r, :], rd_el_bot[:, :N_r, :], cfg)
    if cfg.gaussian_sigma > 0:
        RE = gaussian_filter(RE, cfg.gaussian_sigma).astype(np.float32)
    res.RE = RE
    if verbose: print(f"[PROC] 9. RE map → {RE.shape}")

    if ra_det.sum() > 0:
        ra_det = _restrict_ra_candidates(ra_det, RA, RE, cfg)
        if verbose:
            print(f"[PROC] 9b. Strict-object filter ? {ra_det.sum()} detections")

    res.ra_det = ra_det
    res.ra_thresh = ra_thresh

    # 10. arrDREA
    if az_cube_drea is not None:
        res.arr_drea = build_arr_drea(az_cube_drea, RE, cfg)
        if verbose: print(f"[PROC] 10. arrDREA → {res.arr_drea.shape}")

    # 11. xyz cloud
    res.xyz_cloud = extract_xyz(ra_det, RA, RE, cfg.doppler_axis, RD_mti, rd_det, cfg)
    if verbose: print(f"[PROC] 11. Point cloud → {len(res.xyz_cloud)} pts")

    # Auto-save
    if cfg.save_drea_path and res.arr_drea is not None:
        save_arr_drea(res.arr_drea, cfg.save_drea_path)
    if cfg.save_xyz_path and res.xyz_cloud is not None and len(res.xyz_cloud):
        save_xyz_cloud(res.xyz_cloud, cfg.save_xyz_path)

    return res
