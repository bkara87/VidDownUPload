import subprocess
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

class VideoProcessor:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def process_video(
        self,
        input_path: str,
        output_path: str,
        blur_box: Optional[Tuple[int, int, int, int]] = None,  # (x, y, width, height) to mask old watermark
        watermark_logo_path: Optional[str] = None,             # PNG logo file path
        logo_position: str = "bottom_right",                   # top_left, top_right, bottom_left, bottom_right, center
        logo_scale: float = 0.15,                              # Scale relative to video width
        text_watermark: Optional[str] = None                   # Text watermark
    ) -> bool:
        """
        Applies watermark mask (blur box) and custom logo/text watermark onto the input video.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")

        filter_complex_steps = []
        current_stream = "[0:v]"

        # Step 1: Apply Delogo / Blur Box to cover original watermark
        if blur_box:
            bx, by, bw, bh = blur_box
            # delogo filter in ffmpeg
            filter_complex_steps.append(f"{current_stream}delogo=x={bx}:y={by}:w={bw}:h={bh}[blurred]")
            current_stream = "[blurred]"

        # Step 2: Overlay custom image logo
        cmd = [self.ffmpeg_path, "-y", "-i", input_path]
        
        if watermark_logo_path and os.path.exists(watermark_logo_path):
            cmd.extend(["-i", watermark_logo_path])
            
            # Position calculation for overlay
            pos_map = {
                "top_left": "10:10",
                "top_right": "main_w-overlay_w-10:10",
                "bottom_left": "10:main_h-overlay_h-10",
                "bottom_right": "main_w-overlay_w-10:main_h-overlay_h-10",
                "center": "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
            }
            overlay_pos = pos_map.get(logo_position, pos_map["bottom_right"])

            filter_complex_steps.append(
                f"[1:v]scale=iw*{logo_scale}:-1[scaled_logo];"
                f"{current_stream}[scaled_logo]overlay={overlay_pos}[outv]"
            )
            current_stream = "[outv]"

        # Step 3: Text watermark if provided
        if text_watermark:
            filter_complex_steps.append(
                f"{current_stream}drawtext=text='{text_watermark}':x=w-tw-20:y=h-th-20:fontsize=24:fontcolor=white@0.8[outv_text]"
            )
            current_stream = "[outv_text]"

        if filter_complex_steps:
            filter_str = ";".join(filter_complex_steps)
            cmd.extend(["-filter_complex", filter_str, "-map", current_stream, "-map", "0:a?"])
        else:
            cmd.extend(["-c", "copy"])

        cmd.extend(["-c:a", "copy", output_path])

        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr}")
            return False
