# ch1116.py
from machine import Pin, I2C
import time
import framebuf

class CH1116_I2C(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        # buffer: one bit per pixel, row-major, pages (height/8) pages
        self.buffer = bytearray(self.width * (self.height // 8))
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    def write_cmd(self, cmd):
        # 0x00 prefix means “next byte is command”
        self.i2c.writeto(self.addr, bytes([0x00, cmd]))

    def write_data(self, buf):
        # 0x40 prefix means “next bytes are data”
        # If buf is large, may need to chunk
        self.i2c.writeto(self.addr, b'\x40' + buf)

    def init_display(self):
        # Reset (if your module has RESET pin — else skip)
        # Some modules don’t expose reset via I2C, so skip if no pin.
        # Now send initialization commands
        cmds = [
            0xAE,             # Display OFF
            0xA1,             # Segment remap (or 0xA0) — depends on module
            0xC8,             # COM output scan direction (or C0)
            0xA4,             # Display all on resume (normal)
            0xA8, 0x3F,       # MUX ratio = 63 (for 64 rows)
            0xD3, 0x00,       # Display offset = 0
            0xD5, 0x80,       # Display clock divide (oscillator)
            0xD9, 0x22,       # Pre-charge period
            0xDA, 0x12,       # COM pins hardware config
            0xDB, 0x20,       # VCOMH deselect level
            0x8D, 0x14,       # Charge pump (enable)
            0xAF              # Display ON
        ]
        for cmd in cmds:
            self.write_cmd(cmd)
            time.sleep_ms(10)

        # Clear the display
        self.fill(0)
        self.show()

    def show(self):
        # Write the buffer out, page by page
        pages = self.height // 8
        for page in range(pages):
            self.write_cmd(0xB0 + page)       # set page address
            self.write_cmd(0x00)              # set lower column start address
            self.write_cmd(0x10)              # set higher column start address
            start = page * self.width
            end = start + self.width
            self.write_data(self.buffer[start:end])

    def poweroff(self):
        self.write_cmd(0xAE)

    def poweron(self):
        self.write_cmd(0xAF)

    def contrast(self, contrast):
        # contrast in 0..255
        self.write_cmd(0x81)
        self.write_cmd(contrast & 0xFF)

