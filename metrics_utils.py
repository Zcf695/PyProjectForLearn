"""
Video quality metrics computation module for RIFE frame interpolation.
Computes comparison data between original and processed videos to quantify
the improvement achieved through frame interpolation.
"""

import os
import cv2
import numpy as np


def compute_ssim(img1, img2):
    """
    Compute SSIM between two images (BGR format) using pure numpy/OpenCV.
    Implements the standard SSIM formula with C1/C2 stabilization constants.
    Returns float in [0, 1], higher is better.
    """
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY).astype(np.float64)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY).astype(np.float64)

    # SSIM constants
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    # Use a 11x11 Gaussian-like window (approximated with uniform for speed)
    kernel = cv2.getGaussianKernel(11, 1.5)
    window = np.outer(kernel, kernel.transpose())

    mu1 = cv2.filter2D(gray1, -1, window, borderType=cv2.BORDER_REPLICATE)[5:-5, 5:-5]
    mu2 = cv2.filter2D(gray2, -1, window, borderType=cv2.BORDER_REPLICATE)[5:-5, 5:-5]

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.filter2D(gray1 ** 2, -1, window, borderType=cv2.BORDER_REPLICATE)[5:-5, 5:-5] - mu1_sq
    sigma2_sq = cv2.filter2D(gray2 ** 2, -1, window, borderType=cv2.BORDER_REPLICATE)[5:-5, 5:-5] - mu2_sq
    sigma12 = cv2.filter2D(gray1 * gray2, -1, window, borderType=cv2.BORDER_REPLICATE)[5:-5, 5:-5] - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / \
               ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))

    return float(np.mean(ssim_map))


def compute_psnr(img1, img2):
    """
    Compute PSNR between two images (BGR format).
    Returns float in dB, higher is better.
    """
    mse = np.mean((img1.astype(np.float64) - img2.astype(np.float64)) ** 2)
    if mse == 0:
        return 100.0
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return float(psnr)


def compute_temporal_smoothness(video_path, max_frames=100):
    """
    Compute temporal smoothness metrics by analyzing consecutive frame pairs.

    Returns dict with:
      - avg_ssim: mean SSIM between consecutive frames (lower = more motion/changes)
      - ssim_std: standard deviation of SSIM values
      - smoothness_score: composite score (0-100), higher = more stable transitions
      - frame_count: number of frames analyzed
    """
    cap = cv2.VideoCapture(video_path)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    if frame_count < 2:
        cap.release()
        return {
            'avg_ssim': 0.0,
            'ssim_std': 0.0,
            'smoothness_score': 0.0,
            'frame_count': frame_count,
            'fps': fps,
        }

    # Sample up to max_frames frames
    sample_indices = np.linspace(0, frame_count - 2, min(max_frames, frame_count - 1), dtype=int)

    ssim_values = []
    prev_frame = None
    prev_idx = -2

    for idx in sample_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret1, frame1 = cap.read()
        ret2, frame2 = cap.read()

        if not ret1 or not ret2:
            continue

        ssim_val = compute_ssim(frame1, frame2)
        ssim_values.append(ssim_val)

    cap.release()

    if not ssim_values:
        return {
            'avg_ssim': 0.0,
            'ssim_std': 0.0,
            'smoothness_score': 0.0,
            'frame_count': frame_count,
            'fps': fps,
        }

    avg_ssim = float(np.mean(ssim_values))
    ssim_std = float(np.std(ssim_values))

    # Smoothness score: higher consistency (lower std) and appropriate SSIM range
    # Convert to 0-100 scale: lower SSIM variance = smoother motion
    smoothness = max(0, min(100, avg_ssim * 100 - ssim_std * 50))

    return {
        'avg_ssim': avg_ssim,
        'ssim_std': ssim_std,
        'smoothness_score': smoothness,
        'frame_count': frame_count,
        'fps': fps,
    }


def compute_psnr_sample(original_video, processed_video, max_frames=30):
    """
    Compute average PSNR between sampled frames from original and processed videos.
    Since processed video has interpolated frames, we compare at corresponding
    positions (every N frames where N = processed_fps / original_fps).

    Returns avg PSNR in dB.
    """
    cap_orig = cv2.VideoCapture(original_video)
    cap_proc = cv2.VideoCapture(processed_video)

    orig_frames = int(cap_orig.get(cv2.CAP_PROP_FRAME_COUNT))
    proc_frames = int(cap_proc.get(cv2.CAP_PROP_FRAME_COUNT))

    if orig_frames < 2 or proc_frames < 2:
        cap_orig.release()
        cap_proc.release()
        return {'avg_psnr': 0.0, 'samples': 0}

    # Sample corresponding frame positions
    sample_count = min(max_frames, orig_frames - 1)
    psnr_values = []

    for i in range(sample_count):
        orig_pos = int(i * (orig_frames - 1) / sample_count)
        proc_pos = int(i * (proc_frames - 1) / sample_count)

        cap_orig.set(cv2.CAP_PROP_POS_FRAMES, orig_pos)
        cap_proc.set(cv2.CAP_PROP_POS_FRAMES, proc_pos)

        ret1, frame1 = cap_orig.read()
        ret2, frame2 = cap_proc.read()

        if ret1 and ret2:
            # Resize to match dimensions if needed
            if frame1.shape != frame2.shape:
                frame2 = cv2.resize(frame2, (frame1.shape[1], frame1.shape[0]))
            psnr = compute_psnr(frame1, frame2)
            psnr_values.append(psnr)

    cap_orig.release()
    cap_proc.release()

    avg_psnr = float(np.mean(psnr_values)) if psnr_values else 0.0
    return {
        'avg_psnr': avg_psnr,
        'samples': len(psnr_values),
    }


def compute_all_metrics(original_video, processed_video, processing_time=None):
    """
    Master function: compute all comparison metrics between original and processed video.

    Args:
        original_video: path to original video file
        processed_video: path to processed (interpolated) video file
        processing_time: optional float, total processing time in seconds

    Returns:
        dict with all comparison metrics
    """
    result = {}

    # --- File info comparison ---
    orig_size = os.path.getsize(original_video) if os.path.exists(original_video) else 0
    proc_size = os.path.getsize(processed_video) if os.path.exists(processed_video) else 0

    result['orig_file_size'] = orig_size
    result['proc_file_size'] = proc_size
    result['size_ratio'] = round(proc_size / orig_size, 2) if orig_size > 0 else 0

    # --- Temporal smoothness ---
    orig_smooth = compute_temporal_smoothness(original_video)
    proc_smooth = compute_temporal_smoothness(processed_video)

    result['orig_frame_count'] = orig_smooth['frame_count']
    result['proc_frame_count'] = proc_smooth['frame_count']
    result['orig_fps'] = orig_smooth['fps']
    result['proc_fps'] = proc_smooth['fps']
    result['frame_increase_ratio'] = (
        round(proc_smooth['frame_count'] / orig_smooth['frame_count'], 2)
        if orig_smooth['frame_count'] > 0 else 0
    )
    result['fps_increase_ratio'] = (
        round(proc_smooth['fps'] / orig_smooth['fps'], 2)
        if orig_smooth['fps'] > 0 else 0
    )

    result['orig_avg_ssim'] = orig_smooth['avg_ssim']
    result['proc_avg_ssim'] = proc_smooth['avg_ssim']
    result['orig_ssim_std'] = orig_smooth['ssim_std']
    result['proc_ssim_std'] = proc_smooth['ssim_std']
    result['orig_smoothness'] = orig_smooth['smoothness_score']
    result['proc_smoothness'] = proc_smooth['smoothness_score']

    # --- PSNR sample ---
    psnr_data = compute_psnr_sample(original_video, processed_video)
    result['avg_psnr'] = psnr_data['avg_psnr']
    result['psnr_samples'] = psnr_data['samples']

    # --- Processing time ---
    result['processing_time'] = processing_time

    # --- Overall quality grade ---
    result['grade'] = _compute_grade(result)

    return result


def _compute_grade(metrics):
    """
    Compute an overall quality grade based on metrics.
    Returns a string: 'A+', 'A', 'B', 'C', 'D'
    """
    score = 0

    # Smoothness improvement
    smooth_diff = metrics.get('proc_smoothness', 0) - metrics.get('orig_smoothness', 0)
    if smooth_diff > 10:
        score += 3
    elif smooth_diff > 5:
        score += 2
    elif smooth_diff > 0:
        score += 1

    # FPS increase
    fps_ratio = metrics.get('fps_increase_ratio', 1)
    if fps_ratio >= 8:
        score += 3
    elif fps_ratio >= 4:
        score += 2
    elif fps_ratio >= 2:
        score += 1

    # PSNR quality
    psnr = metrics.get('avg_psnr', 0)
    if psnr >= 40:
        score += 2
    elif psnr >= 30:
        score += 1

    if score >= 7:
        return 'A+'
    elif score >= 5:
        return 'A'
    elif score >= 3:
        return 'B'
    elif score >= 1:
        return 'C'
    else:
        return 'D'


def format_size(size_bytes):
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_time(seconds):
    """Format seconds to human-readable string."""
    if seconds is None:
        return "N/A"
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}分{secs}秒"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}时{mins}分"
