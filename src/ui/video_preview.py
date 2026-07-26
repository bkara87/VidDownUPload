import os
import cv2
import threading
import time
import tempfile
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import customtkinter as ctk

try:
    import pygame
    PYGAME_AVAILABLE = True
except Exception:
    PYGAME_AVAILABLE = False

from src.ui.preset_badges import render_badge_overlay
from src.config import FFMPEG_BINARY

class VideoPreviewWidget(ctk.CTkFrame):
    """
    Interactive 9:16 Live Video Player & Canvas with:
    - 30 FPS Live Video Loop Playback (CPU-Optimized with frame caching)
    - Mute / Unmute Audio Toggle
    - Interactive Mouse Drag & Drop Positioning for Logo and Blur Box Mask
    - Real-time Visual Badge Overlay
    - OPTIMIZED: Badge/Logo PIL önbelleği — her frame yeniden oluşturulmaz
    """
    def __init__(self, master, width=270, height=480, on_pos_changed=None, **kwargs):
        super().__init__(master, **kwargs)
        self.preview_width = width
        self.preview_height = height
        self.on_pos_changed = on_pos_changed

        self.current_video_path = None
        self.current_audio_path = None
        
        # Playback states
        self.is_playing = False
        self.is_muted = True
        self.cap = None
        self.total_frames = 0
        self.fps = 30.0
        self.current_frame_idx = 0
        self._play_thread = None
        self._stop_event = threading.Event()

        # Normalized coordinates (0.0 to 1.0)
        self.logo_rel_x = 0.70
        self.logo_rel_y = 0.85
        self.logo_scale = 0.22

        self.blur_rel_x = 0.60
        self.blur_rel_y = 0.83
        self.blur_rel_w = 0.35
        self.blur_rel_h = 0.12

        # Dragging & Selection state
        self.selected_target = 'logo'  # 'logo', 'blur', or None
        self.dragging_mode = None     # 'move', 'resize', or None
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Overlay parameters
        self.mask_enabled = True
        self.logo_enabled = True
        self.logo_path = None
        self.text_wm = None
        self.badge_preset = None

        # ——— PERFORMANCE CACHE ———
        # Badge cache: badge_preset key → (PIL Image, w, h)
        self._cached_badge_img = None
        self._cached_badge_key = None   # (preset, w, h)

        # Logo cache: logo_path + scale key → resized PIL logo Image
        self._cached_logo_img = None
        self._cached_logo_key = None    # (logo_path, scale, preview_w)

        # Settings change flag for single-frame refresh
        self._settings_changed = False

        self._build_ui()
        self._bind_mouse_events()

        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init()
            except Exception:
                pass

    def _build_ui(self):
        self.configure(fg_color="#070B12", corner_radius=12, border_width=1, border_color="#1E293B")

        self.canvas_label = ctk.CTkLabel(
            self,
            text="🎬 9:16 Canlı Video Oynatıcı\n\n[Tıkla: Seç / Köşeden Büyüt]\nLogo & Blur Kutusunu Taşıyın",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#64748B",
            width=self.preview_width,
            height=self.preview_height,
            corner_radius=10,
            fg_color="#090D16"
        )
        self.canvas_label.pack(padx=8, pady=(8, 4), fill="both", expand=True)

        # Player Controls Bar (Play/Pause, Mute/Unmute)
        ctrl_bar = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_bar.pack(fill="x", padx=8, pady=(0, 6))

        self.btn_play = ctk.CTkButton(
            ctrl_bar,
            text="▶️ Oynat",
            width=80,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1E293B",
            hover_color="#334155",
            command=self.toggle_play
        )
        self.btn_play.pack(side="left", padx=(0, 4))

        self.btn_mute = ctk.CTkButton(
            ctrl_bar,
            text="🔇 Sessiz",
            width=80,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#334155",
            hover_color="#475569",
            command=self.toggle_mute
        )
        self.btn_mute.pack(side="left", padx=2)

        self.lbl_drag_info = ctk.CTkLabel(
            ctrl_bar,
            text="📍 Seç & Köşeden Büyüt",
            font=ctk.CTkFont(size=10),
            text_color="#94A3B8"
        )
        self.lbl_drag_info.pack(side="right", padx=(0, 4))

    def _bind_mouse_events(self):
        self.canvas_label.bind("<Button-1>", self._on_mouse_down)
        self.canvas_label.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas_label.bind("<ButtonRelease-1>", self._on_mouse_up)

    def load_video(self, video_path):
        if not video_path or not os.path.exists(video_path):
            return

        self.stop_player()
        self.current_video_path = video_path

        # Invalidate caches on new video
        self._cached_badge_img = None
        self._cached_badge_key = None
        self._cached_logo_img = None
        self._cached_logo_key = None

        try:
            if self.cap:
                self.cap.release()
            self.cap = cv2.VideoCapture(video_path)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
            self.current_frame_idx = 0

            # ASYNCHRONOUS AUDIO EXTRACTION (Zero-lag UI loading)
            threading.Thread(target=self._prepare_audio, args=(video_path,), daemon=True).start()

            # Refresh single frame instantly
            self._single_frame_refresh()

            # Start playback automatically
            self.start_player()
        except Exception as e:
            print(f"Error loading video player: {e}")

    def _prepare_audio(self, video_path):
        if not PYGAME_AVAILABLE:
            return
        try:
            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            self.current_audio_path = temp_wav.name
            temp_wav.close()

            # Extract audio using ffmpeg to temp wav in background
            cmd = [FFMPEG_BINARY, "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2", self.current_audio_path]
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )

            if os.path.exists(self.current_audio_path) and os.path.getsize(self.current_audio_path) > 1000:
                if self.is_playing:
                    pygame.mixer.music.load(self.current_audio_path)
                    pygame.mixer.music.play(-1)
                    pygame.mixer.music.set_volume(0.0 if self.is_muted else 1.0)
        except Exception as e:
            print(f"Audio prepare error: {e}")

    def start_player(self):
        if not self.cap or not self.cap.isOpened():
            return
        self.is_playing = True
        self._stop_event.clear()
        self.btn_play.configure(text="⏸️ Durdur")

        if PYGAME_AVAILABLE and self.current_audio_path and os.path.exists(self.current_audio_path):
            try:
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(0.0 if self.is_muted else 1.0)
            except Exception:
                pass

        if self._play_thread is None or not self._play_thread.is_alive():
            self._play_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._play_thread.start()

    def stop_player(self):
        self.is_playing = False
        self._stop_event.set()
        self.btn_play.configure(text="▶️ Oynat")
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def toggle_play(self):
        if self.is_playing:
            self.stop_player()
        else:
            self.start_player()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.btn_mute.configure(text="🔇 Sessiz", fg_color="#334155")
            if PYGAME_AVAILABLE:
                try:
                    pygame.mixer.music.set_volume(0.0)
                except Exception:
                    pass
        else:
            self.btn_mute.configure(text="🔊 Ses Açık", fg_color="#10B981")
            if PYGAME_AVAILABLE:
                try:
                    pygame.mixer.music.set_volume(1.0)
                except Exception:
                    pass

    def _playback_loop(self):
        """
        Optimized playback loop:
        - Badge & Logo PIL images are cached — only regenerated when settings change
        - Frame rate is capped at video FPS (not exceeding 30)
        - Uses boxFilter for faster blur (5x speedup vs GaussianBlur)
        """
        target_fps = min(30.0, max(10.0, self.fps))
        frame_delay = 1.0 / target_fps

        while not self._stop_event.is_set() and self.cap and self.cap.isOpened():
            if not self.is_playing:
                time.sleep(0.05)
                continue

            t_start = time.time()

            ret, frame = self.cap.read()
            if not ret:
                # Loop video from frame 0
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                if PYGAME_AVAILABLE and self.current_audio_path:
                    try:
                        pygame.mixer.music.play(-1)
                    except Exception:
                        pass
                continue

            # Convert BGR frame to RGB Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(frame_rgb)

            # Render overlay on frame (uses cache for badge/logo)
            processed_pil = self._render_frame_overlay(pil_frame)

            # FAST BILINEAR RESIZE FOR HIGH FPS LOW CPU USAGE
            img_preview = processed_pil.resize(
                (self.preview_width, self.preview_height),
                Image.Resampling.BILINEAR
            )
            ctk_img = ctk.CTkImage(
                light_image=img_preview,
                dark_image=img_preview,
                size=(self.preview_width, self.preview_height)
            )

            self.after(0, lambda img=ctk_img: self.canvas_label.configure(image=img, text=""))

            # Adaptive sleep to maintain target FPS without busy-waiting
            elapsed = time.time() - t_start
            sleep_time = max(0.005, frame_delay - elapsed)
            time.sleep(sleep_time)

    def _get_cached_badge(self, w: int, h: int):
        """Returns cached badge overlay PIL image, regenerating only if preset/size changed."""
        cache_key = (self.badge_preset, w, h)
        if self._cached_badge_key != cache_key:
            try:
                self._cached_badge_img = render_badge_overlay(self.badge_preset, w, h)
            except Exception as e:
                print(f"Badge cache error: {e}")
                self._cached_badge_img = None
            self._cached_badge_key = cache_key
        return self._cached_badge_img

    def _get_cached_logo(self, w: int):
        """Returns cached resized logo PIL image, regenerating only if path/scale changed."""
        if not self.logo_path or not os.path.exists(self.logo_path):
            self._cached_logo_img = None
            self._cached_logo_key = None
            return None

        cache_key = (self.logo_path, round(self.logo_scale, 3), w)
        if self._cached_logo_key != cache_key:
            try:
                logo_raw = Image.open(self.logo_path).convert("RGBA")
                target_w = int(w * self.logo_scale)
                aspect = logo_raw.height / max(1, logo_raw.width)
                target_h = max(20, int(target_w * aspect))
                self._cached_logo_img = logo_raw.resize(
                    (target_w, target_h),
                    Image.Resampling.LANCZOS  # Higher quality for logo cache (done once)
                )
            except Exception as e:
                print(f"Logo cache error: {e}")
                self._cached_logo_img = None
            self._cached_logo_key = cache_key
        return self._cached_logo_img

    def _render_frame_overlay(self, base_pil: Image.Image) -> Image.Image:
        img = base_pil.copy().convert("RGBA")
        w, h = img.size

        # 1. Apply Blur Box Mask (Mouse positioned) — FAST boxFilter instead of GaussianBlur
        if self.mask_enabled:
            img_rgb = img.convert("RGB")
            img_np = np.array(img_rgb)

            box_w = int(w * self.blur_rel_w)
            box_h = int(h * self.blur_rel_h)

            x1 = int(w * self.blur_rel_x)
            y1 = int(h * self.blur_rel_y)
            x2 = min(w, x1 + box_w)
            y2 = min(h, y1 + box_h)

            roi = img_np[y1:y2, x1:x2]
            if roi.size > 0:
                # cv2.boxFilter is ~5x faster than GaussianBlur for preview
                ksize = (41, 41)
                blurred_roi = cv2.boxFilter(roi, -1, ksize, normalize=True)
                img_np[y1:y2, x1:x2] = blurred_roi
                img = Image.fromarray(img_np).convert("RGBA")

            # Draw prominent selection box & resize handle if selected
            if self.selected_target == "blur":
                draw_tmp = ImageDraw.Draw(img)
                draw_tmp.rectangle([x1, y1, x2, y2], outline=(6, 182, 212, 255), width=4)
                # Corner handle (bottom-right resizer square)
                draw_tmp.rectangle([x2 - 16, y2 - 16, x2 + 4, y2 + 4], fill=(6, 182, 212, 255), outline=(255, 255, 255, 255), width=2)

        # 2. Overlay Visual Sticker Badge — CACHED, not regenerated every frame
        if self.badge_preset and self.badge_preset != "none":
            badge_img = self._get_cached_badge(w, h)
            if badge_img:
                try:
                    img.alpha_composite(badge_img)
                except Exception as e:
                    print(f"Error drawing badge overlay: {e}")

        # 3. Overlay Logo PNG — CACHED resized logo, pasted per frame
        if self.logo_enabled:
            logo_img = self._get_cached_logo(w)
            if logo_img:
                try:
                    lx = int(w * self.logo_rel_x)
                    ly = int(h * self.logo_rel_y)
                    target_logo_w, target_logo_h = logo_img.size

                    # Clamp to image bounds
                    lx = min(lx, w - target_logo_w)
                    ly = min(ly, h - target_logo_h)
                    lx = max(0, lx)
                    ly = max(0, ly)

                    # Paste logo
                    img.paste(logo_img, (lx, ly), logo_img)

                    # Draw selection box & resize handle if selected
                    if self.selected_target == "logo":
                        draw_tmp = ImageDraw.Draw(img)
                        draw_tmp.rectangle(
                            [lx, ly, lx + target_logo_w, ly + target_logo_h],
                            outline=(245, 158, 11, 255), width=4
                        )
                        # Corner handle (bottom-right resizer square)
                        rx2 = lx + target_logo_w
                        ry2 = ly + target_logo_h
                        draw_tmp.rectangle(
                            [rx2 - 16, ry2 - 16, rx2 + 4, ry2 + 4],
                            fill=(245, 158, 11, 255), outline=(255, 255, 255, 255), width=2
                        )
                except Exception as e:
                    print(f"Error overlaying logo: {e}")

        # 4. Overlay Text Watermark
        if self.text_wm and self.text_wm.strip():
            draw = ImageDraw.Draw(img)
            text = self.text_wm.strip()
            font_size = int(h * 0.04)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            tx, ty = int(w * 0.05), int(h * 0.90)
            draw.text((tx + 2, ty + 2), text, font=font, fill=(0, 0, 0, 200))
            draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 240))

        return img.convert("RGB")

    def update_settings(self, mask_enabled=True, logo_enabled=True, logo_path=None,
                        text_wm=None, badge_preset=None, logo_scale=None,
                        blur_w=None, blur_h=None):
        """Update overlay settings and invalidate caches as needed."""
        # Detect badge change → invalidate badge cache
        if badge_preset != self.badge_preset:
            self._cached_badge_img = None
            self._cached_badge_key = None

        # Detect logo path/scale change → invalidate logo cache
        if logo_path != self.logo_path or (logo_scale is not None and logo_scale != self.logo_scale):
            self._cached_logo_img = None
            self._cached_logo_key = None

        self.mask_enabled = mask_enabled
        self.logo_enabled = logo_enabled
        self.logo_path = logo_path
        self.text_wm = text_wm
        self.badge_preset = badge_preset
        if logo_scale is not None:
            self.logo_scale = logo_scale
        if blur_w is not None:
            self.blur_rel_w = blur_w
        if blur_h is not None:
            self.blur_rel_h = blur_h

        # If not playing, render single frame refresh
        if not self.is_playing and self.current_video_path:
            self._single_frame_refresh()

    def _single_frame_refresh(self):
        if not self.cap or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        if ret and frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_frame = Image.fromarray(frame_rgb)
            processed_pil = self._render_frame_overlay(pil_frame)
            img_preview = processed_pil.resize(
                (self.preview_width, self.preview_height),
                Image.Resampling.BILINEAR
            )
            ctk_img = ctk.CTkImage(
                light_image=img_preview,
                dark_image=img_preview,
                size=(self.preview_width, self.preview_height)
            )
            self.canvas_label.configure(image=ctk_img, text="")

    # --- EASY MOUSE DRAG & RESIZE EVENT HANDLERS ---
    def _on_mouse_down(self, event):
        rx = event.x / float(self.preview_width)
        ry = event.y / float(self.preview_height)

        # Tolerance padding (+0.08 normalized ratio for easy clicking)
        pad = 0.08

        # 1. Test Logo Hit Box & Corner Handle
        lx, ly = self.logo_rel_x, self.logo_rel_y
        lw, lh = self.logo_scale, self.logo_scale * 0.5
        rx2, ry2 = lx + lw, ly + lh

        # Corner handle click (bottom-right square)
        if abs(rx - rx2) <= pad and abs(ry - ry2) <= pad and self.selected_target == "logo":
            self.selected_target = "logo"
            self.dragging_mode = "resize"
            self.lbl_drag_info.configure(text="📐 Logo Büyütülüyor...", text_color="#F59E0B")
            return

        # Main Logo box click
        if lx - pad <= rx <= rx2 + pad and ly - pad <= ry <= ry2 + pad:
            self.selected_target = "logo"
            self.dragging_mode = "move"
            self.lbl_drag_info.configure(text="✨ Logo Taşınıyor...", text_color="#F59E0B")
            if not self.is_playing:
                self._single_frame_refresh()
            return

        # 2. Test Blur Box Hit Box & Corner Handle
        bx, by = self.blur_rel_x, self.blur_rel_y
        bw, bh = self.blur_rel_w, self.blur_rel_h
        bx2, by2 = bx + bw, by + bh

        # Corner handle click (bottom-right square)
        if abs(rx - bx2) <= pad and abs(ry - by2) <= pad and self.selected_target == "blur":
            self.selected_target = "blur"
            self.dragging_mode = "resize"
            self.lbl_drag_info.configure(text="📐 Blur Büyütülüyor...", text_color="#06B6D4")
            return

        # Main Blur box click
        if bx - pad <= rx <= bx2 + pad and by - pad <= ry <= by2 + pad:
            self.selected_target = "blur"
            self.dragging_mode = "move"
            self.lbl_drag_info.configure(text="💧 Blur Taşınıyor...", text_color="#06B6D4")
            if not self.is_playing:
                self._single_frame_refresh()
            return

        # Fallback: Select whichever is closer
        dist_logo = (rx - lx)**2 + (ry - ly)**2
        dist_blur = (rx - bx)**2 + (ry - by)**2
        if dist_logo < dist_blur:
            self.selected_target = "logo"
            self.dragging_mode = "move"
            self.logo_rel_x = max(0.0, min(0.9, rx - lw / 2))
            self.logo_rel_y = max(0.0, min(0.9, ry - lh / 2))
        else:
            self.selected_target = "blur"
            self.dragging_mode = "move"
            self.blur_rel_x = max(0.0, min(0.9, rx - bw / 2))
            self.blur_rel_y = max(0.0, min(0.9, ry - bh / 2))

        if not self.is_playing:
            self._single_frame_refresh()

    def _on_mouse_drag(self, event):
        rx = event.x / float(self.preview_width)
        ry = event.y / float(self.preview_height)

        if self.selected_target == "logo":
            if self.dragging_mode == "resize":
                # Scale based on distance from top-left corner
                new_scale = max(0.08, min(0.50, rx - self.logo_rel_x))
                if new_scale != self.logo_scale:
                    # Invalidate logo cache on scale change
                    self._cached_logo_img = None
                    self._cached_logo_key = None
                self.logo_scale = new_scale
            else:
                self.logo_rel_x = max(0.0, min(0.95 - self.logo_scale, rx - self.logo_scale / 2))
                self.logo_rel_y = max(0.0, min(0.95 - self.logo_scale * 0.5, ry - (self.logo_scale * 0.5) / 2))

        elif self.selected_target == "blur":
            if self.dragging_mode == "resize":
                new_w = max(0.10, min(0.70, rx - self.blur_rel_x))
                new_h = max(0.05, min(0.40, ry - self.blur_rel_y))
                self.blur_rel_w = new_w
                self.blur_rel_h = new_h
            else:
                self.blur_rel_x = max(0.0, min(0.95 - self.blur_rel_w, rx - self.blur_rel_w / 2))
                self.blur_rel_y = max(0.0, min(0.95 - self.blur_rel_h, ry - self.blur_rel_h / 2))

        if self.on_pos_changed:
            self.on_pos_changed(self.logo_rel_x, self.logo_rel_y, self.blur_rel_x, self.blur_rel_y)

        if not self.is_playing:
            self._single_frame_refresh()

    def _on_mouse_up(self, event):
        self.dragging_mode = None
        self.lbl_drag_info.configure(text="📍 Seç & Büyüt", text_color="#94A3B8")
        if not self.is_playing:
            self._single_frame_refresh()
