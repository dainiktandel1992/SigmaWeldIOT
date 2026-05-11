# ds3231.py
# MicroPython library for DS3231 RTC module

import time

class DS3231:
    def __init__(self, i2c, address=0x68):
        self.i2c = i2c
        self.addr = address

    def _bcd2dec(self, bcd):
        return (bcd // 16) * 10 + (bcd % 16)

    def _dec2bcd(self, dec):
        return (dec // 10) * 16 + (dec % 10)

    def datetime(self, datetime=None):
        if datetime is None:
            # Read time
            data = self.i2c.readfrom_mem(self.addr, 0x00, 7)
            second = self._bcd2dec(data[0])
            minute = self._bcd2dec(data[1])
            hour = self._bcd2dec(data[2])
            weekday = self._bcd2dec(data[3])
            day = self._bcd2dec(data[4])
            month = self._bcd2dec(data[5] & 0x1F)
            year = self._bcd2dec(data[6]) + 2000
            return (year, month, day, weekday, hour, minute, second, 0)
        else:
            # Set time
            year, month, day, weekday, hour, minute, second, _ = datetime
            year -= 2000
            data = bytearray([
                self._dec2bcd(second),
                self._dec2bcd(minute),
                self._dec2bcd(hour),
                self._dec2bcd(weekday),
                self._dec2bcd(day),
                self._dec2bcd(month),
                self._dec2bcd(year)
            ])
            self.i2c.writeto_mem(self.addr, 0x00, data)
