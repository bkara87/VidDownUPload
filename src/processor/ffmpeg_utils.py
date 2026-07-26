import subprocess
import os
import sys
import tempfile
import cv2
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image

from src.ui.preset_badges import render_badge_overlay
from src.config import FFMPEG_BINARY

# ─────────────────────────────────────────────────────────────────
# Kalite Ön Ayarları (Kullanıcı Seçimi)
# ─────────────────────────────────────────────────────────────────
QUALITY_PRESETS = {
    "🚀 Hızlı (Düşük CPU)":   {"preset": "ultrafast", "crf": "23", "audio_br": "128k"},
    "✨ Yüksek Kalite":        {"preset": "slow",      "crf": "18", "audio_br": "192k"},
    "🏆 Maksimum Kalite":      {"preset": "veryslow",  "crf": "16", "audio_br": "256k"},
}
DEFAULT_QUALITY = "✨ Yüksek Kalite"


class VideoProcessor:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or FFMPEG_BINARY
        # Varsayılan kalite modu
        self.quality_preset = DEFAULT_QUALITY

    def set_quality(self, quality_label: str):
        """Kullanıcı seçimine göre kalite ön ayarını günceller."""
        if quality_label in QUALITY_PRESETS:
            self.quality_preset = quality_label

    @staticmethod
    def get_video_dimensions(video_path: str) -> Tuple[int, int]:
        try:
            cap = cv2.VideoCapture(video_path)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            if w > 0 and h > 0:
                return w, h
        except Exception:
            pass
        return 1080, 1920

    def process_video(
        self,
        input_path: str,
        output_path: str,
        blur_box: Optional[Tuple[int, int, int, int]] = None,
        watermark_logo_path: Optional[str] = None,
        logo_position: str = "bottom_right",
        logo_scale: float = 0.22,
        text_watermark: Optional[str] = None,
        badge_preset: Optional[str] = None,
        logo_rel_pos: Optional[Tuple[float, float]] = None,
        blur_rel_pos: Optional[Tuple[float, float, float, float]] = None,
        quality_label: Optional[str] = None
    ) -> bool:
        """
        Applies watermark mask (blur box), custom logo, text watermark, and visual sticker badge onto input video.
        Supports exact mouse-dragged relative coordinates.

        QUALITY IMPROVEMENTS:
        - Default preset changed from 'ultrafast' to 'slow' for better quality
        - Default CRF changed from 22 to 18 for Instagram/TikTok quality standards
        - Audio bitrate increased from 128k to 192k
        - Added -movflags +faststart for mobile-optimized MP4 streaming
        - Added scale filter to ensure width/height are multiples of 2 (prevents encoding errors)
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")

        # Kalite ayarını belirle
        q_label = quality_label or self.quality_preset
        q_params = QUALITY_PRESETS.get(q_label, QUALITY_PRESETS[DEFAULT_QUALITY])

        vid_w, vid_h = self.get_video_dimensions(input_path)
        filter_complex_steps = []
        current_stream = "[0:v]"
        inputs = [self.ffmpeg_path, "-y", "-i", input_path]
        input_count = 1
        temp_files_to_cleanup = []

        # Step 1: Delogo / Blur box
        if blur_rel_pos:
            rx, ry, rw, rh = blur_rel_pos
            bx = max(0, int(vid_w * rx))
            by = max(0, int(vid_h * ry))
            bw = max(10, int(vid_w * rw))
            bh = max(10, int(vid_h * rh))
            filter_complex_steps.append(
                f"{current_stream}delogo=x={bx}:y={by}:w={bw}:h={bh}[blurred]"
            )
            current_stream = "[blurred]"
        elif blur_box:
            bx, by, bw, bh = blur_box
            filter_complex_steps.append(f"{current_stream}delogo=x={bx}:y={by}:w={bw}:h={bh}[blurred]")
            current_stream = "[blurred]"

        # Step 2: Overlay Badge Sticker if specified
        if badge_preset and badge_preset != "none":
            try:
                badge_img = render_badge_overlay(badge_preset, vid_w, vid_h)
                temp_badge = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                temp_badge_path = temp_badge.name
                temp_badge.close()
                temp_files_to_cleanup.append(temp_badge_path)

                badge_img.save(temp_badge_path, format="PNG")

                inputs.extend(["-i", temp_badge_path])
                badge_stream_idx = input_count
                input_count += 1

                filter_complex_steps.append(
                    f"{current_stream}[{badge_stream_idx}:v]overlay=0:0[out_badge]"
                )
                current_stream = "[out_badge]"
            except Exception as e:
                print(f"Badge render error in FFmpeg: {e}")

        # Step 3: Overlay Logo PNG (Pre-scaled cleanly with PIL in Python)
        if watermark_logo_path and os.path.exists(watermark_logo_path):
            try:
                logo_img = Image.open(watermark_logo_path)
                target_w = max(40, int(vid_w * logo_scale))
                aspect = logo_img.height / max(1, logo_img.width)
                target_h = max(20, int(target_w * aspect))

                # Use LANCZOS for high-quality logo scaling
                logo_resized = logo_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                temp_logo = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                temp_logo_path = temp_logo.name
                temp_logo.close()
                temp_files_to_cleanup.append(temp_logo_path)
                logo_resized.save(temp_logo_path, format="PNG")

                inputs.extend(["-i", temp_logo_path])
                logo_stream_idx = input_count
                input_count += 1

                if logo_rel_pos:
                    lx, ly = logo_rel_pos
                    overlay_pos = f"main_w*{lx}:main_h*{ly}"
                else:
                    pos_map = {
                        "top_left": "10:10",
                        "top_right": "main_w-overlay_w-10:10",
                        "bottom_left": "10:main_h-overlay_h-10",
                        "bottom_right": "main_w-overlay_w-10:main_h-overlay_h-10",
                        "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
                    }
                    overlay_pos = pos_map.get(logo_position, pos_map["bottom_right"])

                filter_complex_steps.append(
                    f"{current_stream}[{logo_stream_idx}:v]overlay={overlay_pos}[out_logo]"
                )
                current_stream = "[out_logo]"
            except Exception as e:
                print(f"Error preparing logo for FFmpeg: {e}")

        # Step 4: Text watermark
        if text_watermark:
            safe_text = text_watermark.replace("'", "").replace(":", "")
            filter_complex_steps.append(
                f"{current_stream}drawtext=text='{safe_text}':x=w-tw-20:y=h-th-20:fontsize=24:fontcolor=white@0.8[outv_text]"
            )
            current_stream = "[outv_text]"

        # Step 5: Ensure width/height are multiples of 2 (required by libx264)
        # This prevents 'width/height not divisible by 2' errors
        filter_complex_steps.append(
            f"{current_stream}scale=trunc(iw/2)*2:trunc(ih/2)*2[outv_final]"
        )
        current_stream = "[outv_final]"

        cmd = list(inputs)
        if filter_complex_steps:
            filter_str = ";".join(filter_complex_steps)
            cmd.extend(["-filter_complex", filter_str, "-map", current_stream, "-map", "0:a?"])
        else:
            # No filters — direct stream copy with scale fix
            cmd.extend([
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                "-map", "0:v",
                "-map", "0:a?"
            ])

        # ─────────────────────────────────────────────
        # HIGH QUALITY ENCODING PARAMETERS
        # ─────────────────────────────────────────────
        cmd.extend([
            "-c:v", "libx264",
            "-preset", q_params["preset"],     # slow (default) — better compression & quality
            "-crf", q_params["crf"],            # 18 (default) — near-lossless for social media
            "-profile:v", "high",               # H.264 High Profile for max compatibility
            "-level", "4.1",                    # Broad device compatibility
            "-pix_fmt", "yuv420p",              # Required for social media platforms
            "-c:a", "aac",
            "-b:a", q_params["audio_br"],       # 192k (default) — high quality audio
            "-ar", "44100",                     # Standard sample rate
            "-movflags", "+faststart",          # Web/mobile optimized: moov atom at file start
            "-y",
            output_path
        ])

        print(f"[FFmpeg] Quality: {q_label} | preset={q_params['preset']} | crf={q_params['crf']} | audio={q_params['audio_br']}")

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr}")
            return False
        finally:
            for tmp_f in temp_files_to_cleanup:
                if os.path.exists(tmp_f):
                    try:
                        os.remove(tmp_f)
                    except Exception:
                        pass
