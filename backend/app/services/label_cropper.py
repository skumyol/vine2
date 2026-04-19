from pathlib import Path


def build_label_crops(image_path: str | None, *, yolo_enabled: bool = False) -> list[str]:
    if not image_path:
        return []
    _ = Path(image_path)
    _ = yolo_enabled
    return []
