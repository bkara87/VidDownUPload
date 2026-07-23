import os
import cv2
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import customtkinter as ctk

class VideoPreviewWidget(ctk.CTkFrame):
    """
    Real-time Interactive Video Frame Preview with Blur Box, Logo, and Text Watermark Overlay
    """
    def __init__(self, master, width=480, height=320, **kwargs):
        super().__init__(master, **kwargs)
        self.preview_width = width
        self.preview_height = height

        self.current_video_path = None
        self.current_frame_pil = None
        self._photo_image = None

        self._build_ui()

    def _build_ui(self):
        self.configure(fg_color="#070B12", corner_radius=12, border_width=1, border_color="#1E293B")

        self.canvas_label = ctk.CTkLabel(
            self,
            text="🎬 Video Yüklenmedi\n\nLütfen bir video indirin veya secontext belirleyin",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#64748B",
            width=self.preview_width,
            height=self.preview_height,
            corner_radius=10,
            fg_color="#090D16"
        )
        self.canvas_label.pack(padx=10, pady=10, fill="both", expand=True)

    def load_video(self, video_path):
        if not video_path or not os.path.exists(video_path):
            return

        self.current_video_path = video_path
        try:
            cap = cv2.VideoCapture(video_path)
            # Read first frame or 10th frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 5)
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()

            cap.release()

            if ret and frame is not None:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.current_frame_pil = Image.fromarray(frame_rgb)
        except Exception as e:
            print(f"Error loading video frame: {e}")
            self.current_frame_pil = None

    def update_preview(self, mask_enabled=False, mask_pos="Sağ Alt (Instagram/TikTok)",
                       logo_enabled=False, logo_path=None, logo_pos="Sağ Alt",
                       text_wm=None):
        """
        Draws real-time overlay over video frame and updates display
        """
        if self.current_frame_pil is None:
            return

        # Make a copy of base frame
        img = self.current_frame_pil.copy()
        w, h = img.size

        # 1. Apply Blur Box Mask
        if mask_enabled:
            img_np = np.array(img)
            # Calculate box coordinates based on position
            box_w, box_h = int(w * 0.35), int(h * 0.12)
            pos_key = mask_pos.lower()

            if "sol üst" in pos_key:
                x1, y1 = int(w * 0.05), int(h * 0.05)
            elif "sağ üst" in pos_key:
                x1, y1 = int(w * 0.60), int(h * 0.05)
            elif "sol alt" in pos_key:
                x1, y1 = int(w * 0.05), int(h * 0.83)
            else:  # Sağ Alt
                x1, y1 = int(w * 0.60), int(h * 0.83)

            x2, y2 = min(w, x1 + box_w), min(h, y1 + box_h)

            roi = img_np[y1:y2, x1:x2]
            if roi.size > 0:
                blurred_roi = cv2.GaussianBlur(roi, (51, 51), 30)
                img_np[y1:y2, x1:x2] = blurred_roi
                img = Image.fromarray(img_np)

        # 2. Overlay Logo PNG
        if logo_enabled and logo_path and os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path).convert("RGBA")
                lw, lh = logo_img.size
                target_logo_w = int(w * 0.22)
                aspect = lh / max(1, lw)
                target_logo_h = int(target_logo_w * aspect)
                logo_img = logo_img.resize((target_logo_w, target_logo_h), Image.Resampling.LANCZOS)

                l_pos = logo_pos.lower().replace(" ", "_")
                if "sol_üst" in l_pos:
                    lx, ly = int(w * 0.05), int(h * 0.05)
                elif "sağ_üst" in l_pos:
                    lx, ly = int(w * 0.95 - target_logo_w), int(h * 0.05)
                elif "sol_alt" in l_pos:
                    lx, ly = int(w * 0.05), int(h * 0.95 - target_logo_h)
                elif "orta" in l_pos:
                    lx, ly = int((w - target_logo_w) / 2), int((h - target_logo_h) / 2)
                else:  # Sağ Alt
                    lx, ly = int(w * 0.95 - target_logo_w), int(h * 0.95 - target_logo_h)

                img.paste(logo_img, (lx, ly), logo_img)
            except Exception as e:
                print(f"Error overlaying logo preview: {e}")

        # 3. Overlay Text Watermark
        if text_wm and text_wm.strip():
            draw = ImageDraw.Draw(img)
            text = text_wm.strip()
            font_size = int(h * 0.04)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            tx, ty = int(w * 0.05), int(h * 0.92)
            draw.text((tx + 2, ty + 2), text, font=font, fill=(0, 0, 0, 200))
            draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 240))

        # Resize for preview widget canvas
        img_preview = img.resize((self.preview_width, self.preview_height), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=img_preview, dark_image=img_preview, size=(self.preview_width, self.preview_height))

        self.canvas_label.configure(image=ctk_img, text="")
        self._photo_image = ctk_img
