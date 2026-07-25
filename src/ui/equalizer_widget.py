import math
import random
import tkinter as tk
import customtkinter as ctk


class AnimatedEqualizerWidget(ctk.CTkFrame):
    """
    Ultra-Premium Animated Audio Spectrum Equalizer.
    Features:
    - Smooth bar height transitions (lerp animation, no jumps)
    - Multi-color gradient: violet → cyan → emerald
    - Idle breathing pulse when not active
    - Mirror-symmetric spectrum for cinematic look
    - Rounded bar tops
    """

    def __init__(self, master, num_bars: int = 32, height: int = 28, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.num_bars = num_bars
        self.canvas_height = height
        self.is_animating = False
        self._idle_phase = 0.0          # For breathing idle animation
        self._current_heights = []      # Smooth lerp target heights
        self._displayed_heights = []    # Currently displayed heights (lerped)
        self._animation_after_id = None

        self.canvas = tk.Canvas(
            self,
            height=self.canvas_height,
            bg="#040710",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="x", expand=True)
        self.bars = []
        self.bar_tops = []   # Small rounded top glow caps
        self.after(50, self._init_bars)

    # ─────────────────────────────────────────────
    def _get_bar_color(self, idx: int, height_ratio: float) -> str:
        """Returns an interpolated color based on bar position and height."""
        # Gradient: violet #7C3AED → cyan #06B6D4 → emerald #10B981
        t = idx / max(1, self.num_bars - 1)

        if t < 0.5:
            # violet → cyan
            s = t * 2
            r = int(0x7C + (0x06 - 0x7C) * s)
            g = int(0x3A + (0xB6 - 0x3A) * s)
            b = int(0xED + (0xD4 - 0xED) * s)
        else:
            # cyan → emerald
            s = (t - 0.5) * 2
            r = int(0x06 + (0x10 - 0x06) * s)
            g = int(0xB6 + (0xB9 - 0xB6) * s)
            b = int(0xD4 + (0x81 - 0xD4) * s)

        # Dim when short bar
        dim = 0.4 + 0.6 * height_ratio
        r = int(r * dim)
        g = int(g * dim)
        b = int(b * dim)
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _get_cap_color(self, idx: int) -> str:
        """Bright glow cap on top of each bar."""
        t = idx / max(1, self.num_bars - 1)
        if t < 0.5:
            s = t * 2
            r = int(0xA7 + (0x22 - 0xA7) * s)
            g = int(0x8B + (0xD3 - 0x8B) * s)
            b = int(0xFA + (0xEE - 0xFA) * s)
        else:
            s = (t - 0.5) * 2
            r = int(0x22 + (0x4A - 0x22) * s)
            g = int(0xD3 + (0xDE - 0xD3) * s)
            b = int(0xEE + (0x80 - 0xEE) * s)
        return f"#{max(0,min(255,r)):02x}{max(0,min(255,g)):02x}{max(0,min(255,b)):02x}"

    # ─────────────────────────────────────────────
    def _init_bars(self):
        self.canvas.delete("all")
        self.bars.clear()
        self.bar_tops.clear()

        self.canvas.update_idletasks()
        w = max(200, self.canvas.winfo_width())
        self._canvas_w = w

        gap = 2
        total_gap = gap * (self.num_bars - 1)
        bar_w = max(2, (w - total_gap) / self.num_bars)

        min_h = 3
        self._current_heights = [min_h] * self.num_bars
        self._displayed_heights = [min_h] * self.num_bars

        for i in range(self.num_bars):
            x1 = i * (bar_w + gap)
            x2 = x1 + bar_w
            y_bottom = self.canvas_height
            y_top = y_bottom - min_h

            color = self._get_bar_color(i, 0.1)
            cap_color = self._get_cap_color(i)

            # Main bar rectangle
            rect = self.canvas.create_rectangle(
                x1, y_top, x2, y_bottom,
                fill=color, outline="", tags=f"bar_{i}"
            )
            # Glow cap on top (1-2px bright line)
            cap = self.canvas.create_rectangle(
                x1, y_top - 1, x2, y_top + 1,
                fill=cap_color, outline="", tags=f"cap_{i}"
            )
            self.bars.append(rect)
            self.bar_tops.append(cap)

        # Start idle breathing
        self._idle_breathe()

    def _idle_breathe(self):
        """Gentle idle breathing pulse when not animating."""
        if self.is_animating:
            return
        if not self.bars:
            self.after(200, self._idle_breathe)
            return

        self._idle_phase += 0.06
        self.canvas.update_idletasks()
        w = max(200, self.canvas.winfo_width())
        gap = 2
        bar_w = max(2, (w - gap * (self.num_bars - 1)) / self.num_bars)
        y_bottom = self.canvas_height

        for i, (rect, cap) in enumerate(zip(self.bars, self.bar_tops)):
            # Sine wave breathing with slight offset per bar
            phase = self._idle_phase + i * 0.25
            h = 2 + 3 * abs(math.sin(phase))
            y_top = y_bottom - h
            x1 = i * (bar_w + gap)
            x2 = x1 + bar_w
            color = self._get_bar_color(i, h / self.canvas_height)
            self.canvas.coords(rect, x1, y_top, x2, y_bottom)
            self.canvas.coords(cap, x1, y_top - 1, x2, y_top + 1)
            self.canvas.itemconfig(rect, fill=color)

        self.after(40, self._idle_breathe)

    # ─────────────────────────────────────────────
    def start_animation(self):
        if not self.is_animating:
            self.is_animating = True
            self._animate_step()

    def stop_animation(self):
        self.is_animating = False
        # Smoothly fade down all bars
        self._current_heights = [3] * self.num_bars
        self.after(10, self._idle_breathe)

    def _animate_step(self):
        if not self.is_animating:
            return
        if not self.bars:
            self.after(60, self._animate_step)
            return

        self.canvas.update_idletasks()
        w = max(200, self.canvas.winfo_width())
        gap = 2
        bar_w = max(2, (w - gap * (self.num_bars - 1)) / self.num_bars)
        y_bottom = self.canvas_height
        max_h = self.canvas_height - 2

        # Set new random target heights with mirror symmetry
        half = self.num_bars // 2
        targets = [random.randint(4, max_h) for _ in range(half)]
        # Mirror: left half matches right half for symmetric look
        full_targets = targets + targets[::-1]
        self._current_heights = full_targets

        # Lerp displayed toward target (smooth)
        lerp = 0.55
        for i in range(self.num_bars):
            self._displayed_heights[i] = (
                self._displayed_heights[i] * (1 - lerp)
                + self._current_heights[i] * lerp
            )
            h = max(3, int(self._displayed_heights[i]))
            height_ratio = h / max_h

            x1 = i * (bar_w + gap)
            x2 = x1 + bar_w
            y_top = y_bottom - h

            color = self._get_bar_color(i, height_ratio)
            cap_color = self._get_cap_color(i)

            self.canvas.coords(self.bars[i], x1, y_top, x2, y_bottom)
            self.canvas.coords(self.bar_tops[i], x1, y_top - 1, x2, y_top + 1)
            self.canvas.itemconfig(self.bars[i], fill=color)
            self.canvas.itemconfig(self.bar_tops[i], fill=cap_color)

        self.after(55, self._animate_step)
