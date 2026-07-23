import random
import tkinter as tk
import customtkinter as ctk

class AnimatedEqualizerWidget(ctk.CTkFrame):
    """
    Dynamic Animated Audio/Video Equalizer Bars & Pulsing Status Waveform
    """
    def __init__(self, master, num_bars=16, height=40, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.num_bars = num_bars
        self.canvas_height = height
        self.is_animating = False

        self.canvas = tk.Canvas(
            self,
            height=self.canvas_height,
            bg="#070B12",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(fill="x", expand=True)

        self.bars = []
        self._init_bars()

    def _init_bars(self):
        self.canvas.update_idletasks()
        w = max(300, self.canvas.winfo_width())
        bar_w = (w / self.num_bars) - 4

        for i in range(self.num_bars):
            x1 = i * (bar_w + 4) + 2
            y1 = self.canvas_height - 6
            x2 = x1 + bar_w
            y2 = self.canvas_height

            # Color gradient from neon cyan to purple
            color = "#6366F1" if i % 2 == 0 else "#38BDF8"
            rect = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            self.bars.append(rect)

    def start_animation(self):
        if not self.is_animating:
            self.is_animating = True
            self._animate_step()

    def stop_animation(self):
        self.is_animating = False
        # Reset bars
        w = max(300, self.canvas.winfo_width())
        bar_w = (w / self.num_bars) - 4
        for i, rect in enumerate(self.bars):
            x1 = i * (bar_w + 4) + 2
            y1 = self.canvas_height - 4
            x2 = x1 + bar_w
            y2 = self.canvas_height
            self.canvas.coords(rect, x1, y1, x2, y2)

    def _animate_step(self):
        if not self.is_animating:
            return

        w = max(300, self.canvas.winfo_width())
        bar_w = (w / self.num_bars) - 4

        for i, rect in enumerate(self.bars):
            x1 = i * (bar_w + 4) + 2
            h_val = random.randint(6, self.canvas_height - 4)
            y1 = self.canvas_height - h_val
            x2 = x1 + bar_w
            y2 = self.canvas_height

            # Dynamic color pulse
            color = "#818CF8" if h_val > (self.canvas_height / 2) else "#38BDF8"
            self.canvas.itemconfig(rect, fill=color)
            self.canvas.coords(rect, x1, y1, x2, y2)

        self.after(80, self._animate_step)
