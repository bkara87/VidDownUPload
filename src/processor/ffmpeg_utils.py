import subprocess
import os
import sys
import tempfile
import cv2
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
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
def safe_print(*args, **kwargs):
    try:
        msg = " ".join(str(a) for a in args)
        if sys.stdout and hasattr(sys.stdout, 'buffer'):
            sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
            sys.stdout.buffer.flush()
        else:
            print(msg.encode("ascii", errors="replace").decode("ascii"), **kwargs)
    except Exception:
        pass


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

    @staticmethod
    def get_video_duration(video_path: str) -> float:
        """Returns video duration in seconds using OpenCV."""
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            if fps > 0 and frame_count > 0:
                return frame_count / fps
        except Exception:
            pass
        return 0.0

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
        blur_boxes: Optional[List[Tuple[float, float, float, float]]] = None,
        quality_label: Optional[str] = None,
        frame_png_path: Optional[str] = None,
        frame_config: Optional[Dict[str, Any]] = None,
        frame_adjustments: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Applies watermark mask (Gaussian blur box), custom logo, text watermark, and visual sticker badge onto input video.
        Supports exact mouse-dragged relative coordinates for up to 5 blur boxes.
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

        # Step 0: Custom Frame PNG Template Overlay
        if frame_png_path and os.path.exists(frame_png_path) and frame_config:
            try:
                va = frame_config.get("videoArea", {})
                vw_ref = float(frame_config.get("canvasWidth", 1080))
                vh_ref = float(frame_config.get("canvasHeight", 1920))

                scale_w = vid_w / max(1.0, vw_ref)
                scale_h = vid_h / max(1.0, vh_ref)

                fbx = int(float(va.get("x", 0)) * scale_w)
                fby = int(float(va.get("y", 0)) * scale_h)
                fbw = max(10, int(float(va.get("width", vw_ref)) * scale_w))
                fbh = max(10, int(float(va.get("height", vh_ref)) * scale_h))

                fbw = fbw if fbw % 2 == 0 else fbw - 1
                fbh = fbh if fbh % 2 == 0 else fbh - 1

                adj = frame_adjustments or {}
                zoom = max(0.5, float(adj.get("zoom", 1.0)))
                off_x = int(float(adj.get("offsetX", 0)) * scale_w)
                off_y = int(float(adj.get("offsetY", 0)) * scale_h)

                inputs.extend(["-i", frame_png_path])
                frame_stream_idx = input_count
                input_count += 1

                v_scaled_w = int(fbw * zoom)
                v_scaled_h = int(fbh * zoom)

                filter_complex_steps.append(
                    f"color=c=0x0B0F19@1.0:s={vid_w}x{vid_h}:d=1[frame_bg]"
                )
                filter_complex_steps.append(
                    f"{current_stream}scale={v_scaled_w}:{v_scaled_h}:force_original_aspect_ratio=increase,crop={fbw}:{fbh}:max(0\\,(iw-{fbw})/2+{off_x}):max(0\\,(ih-{fbh})/2+{off_y})[v_fitted]"
                )
                filter_complex_steps.append(
                    f"[frame_bg][v_fitted]overlay={fbx}:{fby}[v_with_video]"
                )
                filter_complex_steps.append(
                    f"[{frame_stream_idx}:v]scale={vid_w}:{vid_h}[frame_png_scaled]"
                )
                filter_complex_steps.append(
                    f"[v_with_video][frame_png_scaled]overlay=0:0[out_framed]"
                )
                current_stream = "[out_framed]"
                print(f"[FFmpeg Frame Studio] Template applied: videoArea=({fbx},{fby},{fbw},{fbh}), zoom={zoom}")
            except Exception as fe:
                print(f"[FFmpeg Frame Studio] Error applying frame template: {fe}")

        # Step 1: Heavy Smooth Blur Boxes (support multiple B1-B5 blur_boxes)
        boxes_to_process = []
        if blur_boxes and isinstance(blur_boxes, list):
            boxes_to_process.extend(blur_boxes)
        elif blur_rel_pos:
            boxes_to_process.append(blur_rel_pos)

        for b_idx, box_pos in enumerate(boxes_to_process):
            rx, ry, rw, rh = box_pos
            top_left_x = rx - (rw / 2.0)
            top_left_y = ry - (rh / 2.0)
            bx = max(0, min(int(vid_w * top_left_x), vid_w - 10))
            by = max(0, min(int(vid_h * top_left_y), vid_h - 10))
            bw = max(10, int(vid_w * rw))
            bh = max(10, int(vid_h * rh))
            if bx + bw > vid_w:
                bw = vid_w - bx
            if by + bh > vid_h:
                bh = vid_h - by
            bw = max(10, bw)
            bh = max(10, bh)
            bw = bw if bw % 2 == 0 else bw - 1
            bh = bh if bh % 2 == 0 else bh - 1

            print(f"[FFmpeg Blur #{b_idx+1}] Center: ({rx:.3f}, {ry:.3f}) -> TopLeft: x={bx}, y={by}, w={bw}, h={bh} (video: {vid_w}x{vid_h})")

            m_str = f"blur_m_{b_idx}"
            s_str = f"blur_s_{b_idx}"
            r_str = f"blur_r_{b_idx}"
            o_str = f"blur_o_{b_idx}"

            filter_complex_steps.append(
                f"{current_stream}split[{m_str}][{s_str}]"
            )
            filter_complex_steps.append(
                f"[{s_str}]crop={bw}:{bh}:{bx}:{by},avgblur=sizeX=35:sizeY=35[{r_str}]"
            )
            filter_complex_steps.append(
                f"[{m_str}][{r_str}]overlay={bx}:{by}[{o_str}]"
            )
            current_stream = f"[{o_str}]"

        if not boxes_to_process and blur_box:
            bx, by, bw, bh = blur_box
            # Clamp coordinates
            bx = max(0, min(bx, vid_w - 10))
            by = max(0, min(by, vid_h - 10))
            bw = max(10, min(bw, vid_w - bx))
            bh = max(10, min(bh, vid_h - by))
            bw = bw if bw % 2 == 0 else bw - 1
            bh = bh if bh % 2 == 0 else bh - 1

            filter_complex_steps.append(
                f"{current_stream}split[blur_main][blur_src]"
            )
            filter_complex_steps.append(
                f"[blur_src]crop={bw}:{bh}:{bx}:{by},avgblur=sizeX=35:sizeY=35[blurred_region]"
            )
            filter_complex_steps.append(
                f"[blur_main][blurred_region]overlay={bx}:{by}[blurred]"
            )
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
            "-movflags", "+faststart"           # Web/mobile optimized: moov atom at file start
        ])

        # Auto-trim to 59s if video duration exceeds 59.5s
        duration_sec = self.get_video_duration(input_path)
        if duration_sec > 59.5:
            print(f"[FFmpeg Auto-Trim] Video süresi ({duration_sec:.1f}s) > 59s. Telif uyarısı ve Shorts sınırı için otomatik 59.saniyeye kesiliyor.")
            cmd.extend(["-t", "59"])

        cmd.extend([
            "-y",
            output_path
        ])

        safe_q_label = q_label.encode('ascii', 'ignore').decode('ascii').strip() or "Quality"
        safe_print(f"[FFmpeg] Quality: {safe_q_label} | preset={q_params['preset']} | crf={q_params['crf']} | audio={q_params['audio_br']}")
        safe_print(f"[FFmpeg] Full command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            safe_print(f"[FFmpeg] Processing completed successfully.")
            return True
        except subprocess.CalledProcessError as e:
            safe_print(f"[FFmpeg] ERROR (exit code {e.returncode}):")
            safe_print(f"[FFmpeg] STDERR: {e.stderr[-2000:] if e.stderr else 'No stderr'}")
            return False
        finally:
            for tmp_f in temp_files_to_cleanup:
                if os.path.exists(tmp_f):
                    try:
                        os.remove(tmp_f)
                    except Exception:
                        pass

