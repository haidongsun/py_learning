import struct
import zlib

def create_png(width, height, pixel_data):
    """Create a PNG file from raw pixel data (RGBA rows)."""
    raw = b''
    for row in pixel_data:
        raw += b'\x00' + row  # filter byte + scanline

    def png_chunk(ctype, data):
        chunk = ctype + data
        crc = struct.pack('>I', zlib.crc32(chunk) & 0xffffffff)
        return struct.pack('>I', len(data)) + chunk + crc

    header = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)
    compressed = zlib.compress(raw)
    idat = png_chunk(b'IDAT', compressed)
    iend = png_chunk(b'IEND', b'')

    return header + ihdr + idat + iend


def make_icon(size):
    """Create a pixel pattern for an icon - a down arrow on colored background."""
    bg = (26, 115, 232, 255)   # #1a73e8
    fg = (255, 255, 255, 255)  # white
    pixels = []
    m = size // 2
    arrow_h = size // 3
    arrow_w = size // 3
    stem_w = max(2, size // 8)

    for y in range(size):
        row = b''
        for x in range(size):
            r, g, b, a = bg
            # Draw a "down arrow" shape
            top = m - arrow_h
            bot = m + arrow_h
            left = m - arrow_w
            right = m + arrow_w

            # Arrow stem (vertical)
            if top <= y <= bot and m - stem_w <= x <= m + stem_w:
                r, g, b, a = fg
            # Arrow head (triangle)
            if bot <= y <= bot + arrow_h:
                dist_from_center = abs(x - m)
                max_dist = int(arrow_w * (1 - (y - bot) / arrow_h))
                if dist_from_center <= max_dist:
                    r, g, b, a = fg

            row += struct.pack('BBBB', r, g, b, a)
        pixels.append(row)
    return pixels


for size in [16, 48, 128]:
    pixels = make_icon(size)
    png_data = create_png(size, size, pixels)
    path = f'google-chrome-extension/icons/icon{size}.png'
    with open(path, 'wb') as f:
        f.write(png_data)
    print(f'Created {path} ({len(png_data)} bytes)')
