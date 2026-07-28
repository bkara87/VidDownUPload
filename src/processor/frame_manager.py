import os
import json
import base64
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.config import USER_DATA_DIR, BASE_DIR

FRAMES_DIR = USER_DATA_DIR / "Frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)


class FrameManager:
    """
    Manages custom PNG frame templates for VidDownUPload Frame Studio.
    Templates are stored in USER_DATA_DIR / "Frames" / <TemplateName> /
      - frame.png
      - config.json
    """

    @classmethod
    def get_frames_dir(cls) -> Path:
        FRAMES_DIR.mkdir(parents=True, exist_ok=True)
        return FRAMES_DIR

    @classmethod
    def list_templates(cls) -> List[Dict[str, Any]]:
        """Returns all available frame templates with base64 preview image."""
        templates = []
        frames_dir = cls.get_frames_dir()

        # Check both USER_DATA_DIR / Frames and BASE_DIR / Frames if exists
        dirs_to_scan = [frames_dir]
        base_frames = BASE_DIR / "Frames"
        if base_frames.exists() and base_frames != frames_dir:
            dirs_to_scan.append(base_frames)

        seen_names = set()

        for fdir in dirs_to_scan:
            if not fdir.exists():
                continue
            for item in fdir.iterdir():
                if item.is_dir() and item.name not in seen_names:
                    png_file = item / "frame.png"
                    cfg_file = item / "config.json"
                    if png_file.exists() and cfg_file.exists():
                        try:
                            with open(cfg_file, "r", encoding="utf-8") as f:
                                cfg = json.load(f)

                            with open(png_file, "rb") as pf:
                                png_b64 = "data:image/png;base64," + base64.b64encode(pf.read()).decode("utf-8")

                            cfg["name"] = cfg.get("name", item.name)
                            cfg["folder_name"] = item.name
                            cfg["png_path"] = str(png_file.resolve())
                            cfg["png_b64"] = png_b64
                            templates.append(cfg)
                            seen_names.add(item.name)
                        except Exception as e:
                            print(f"DEBUG [FrameManager]: Error reading template {item.name}: {e}")

        return templates

    @classmethod
    def save_template(cls, name: str, category: str, png_bytes: bytes, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Saves a new PNG frame template with config.json."""
        try:
            safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip() or "CustomFrame"
            tpl_dir = cls.get_frames_dir() / safe_name
            tpl_dir.mkdir(parents=True, exist_ok=True)

            png_file = tpl_dir / "frame.png"
            with open(png_file, "wb") as pf:
                pf.write(png_bytes)

            config_data["name"] = safe_name
            config_data["category"] = category or "Genel"

            cfg_file = tpl_dir / "config.json"
            with open(cfg_file, "w", encoding="utf-8") as cf:
                json.dump(config_data, cf, ensure_ascii=False, indent=2)

            print(f"DEBUG [FrameManager]: Successfully saved frame template '{safe_name}' at {tpl_dir}")
            return {"success": True, "name": safe_name, "dir": str(tpl_dir)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def delete_template(cls, name: str) -> Dict[str, Any]:
        """Deletes a frame template folder."""
        try:
            safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
            tpl_dir = cls.get_frames_dir() / safe_name
            if tpl_dir.exists():
                shutil.rmtree(tpl_dir)
                return {"success": True}
            return {"success": False, "error": "Şablon bulunamadı"}
        except Exception as e:
            return {"success": False, "error": str(e)}
