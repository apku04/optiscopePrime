# config/fonts.py

from PIL import ImageFont


def load_fonts():
    try:
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 11)
    except IOError:
        font_normal = ImageFont.load_default()
        font_bold = ImageFont.load_default()
    return font_normal, font_bold
