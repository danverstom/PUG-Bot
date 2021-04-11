from pathlib import Path
from PIL import Image


# https://github.com/carzam87/python-bulk-image-optimizer/blob/master/bulk-image-optimizer.py
def compress(location: str, quality: int = 30) -> Image:
    """Compress an image on the disk"""
    opt = Image.open(location) # dont handle error
    # Convert .pgn to .jpg
    if opt.format.lower() == "png":
        rgb_opt = opt.convert('RGB')
        rgb_opt.save(location)
        opt = Image.open(location)
    opt.save(location, optimize=True, quality=quality)
    opt.close()
    return opt

    
