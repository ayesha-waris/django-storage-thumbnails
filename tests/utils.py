from io import BytesIO

from PIL import Image


def make_image(width=100, height=80, fmt="JPEG", color=(255, 0, 0)):
    """Return a BytesIO holding a freshly generated test image."""
    mode = "RGBA" if fmt == "PNG" else "RGB"
    buffer = BytesIO()
    Image.new(mode, (width, height), color).save(buffer, format=fmt)
    buffer.seek(0)
    return buffer
