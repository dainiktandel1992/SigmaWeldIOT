from machine import ADC, I2C, Pin
import utime
import ds3231
import ch1116

# i2c = I2C(1, scl=Pin(18), sda=Pin(17))
rtc_i2c = I2C(0, scl=Pin(6), sda=Pin(5))

oled = None
oled_enabled = True

try:
    oled_i2c = I2C(1, scl=Pin(18), sda=Pin(17), freq=400000)
    oled = ch1116.CH1116_I2C(128, 64, oled_i2c)
    oled.fill(0)
    oled.text("Initializing...",0,0)
    oled.show()
except Exception as e:
    # print("OLED init failed:", e)
    oled_enabled = False

def update_oled_display_statement(statement):
    global oled, oled_enabled
    if not oled_enabled or oled is None:
        return
    try:
        oled.fill(0)
        oled.text(statement, 0, 0)
        oled.show()
    except Exception as e:
        # print("OLED error:", e)
        pass

def update_oled_display(voltage, current, counter, code = "W", tag = "OK"):
    global oled, oled_enabled
    if not oled_enabled or oled is None:
        return
    try:
        oled.fill(0)
        oled.text("V: {:.2f}V".format(voltage), 0, 5)
        oled.text("I: {:.2f}A".format(current), 0, 20)
        oled.text("AT: {}".format(counter), 0, 35)
        oled.text("{}: {}".format(code,tag), 0, 50)
        oled.show()
    except Exception as e:
        # print("OLED error:", e)
        pass

def bcd2dec(bcd):
    return ((bcd >> 4) * 10) + (bcd & 0x0F)

def read_time_tuple():
    data = rtc_i2c.readfrom_mem(0x68, 0x00, 7)
    custom_time = (
        bcd2dec(data[6]),
        bcd2dec(data[5] & 0x1F),
        bcd2dec(data[4]),
        bcd2dec(data[2] & 0x3F),
        bcd2dec(data[1]),
        bcd2dec(data[0] & 0x7F),
    )
    year = 2000 + custom_time[0]
    return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
        year,
        custom_time[1],
        custom_time[2],
        custom_time[3],
        custom_time[4],
        custom_time[5],
    )


def set_time(api_time):
    i2c = I2C(0, scl=Pin(6), sda=Pin(5))
    rtc = ds3231.DS3231(i2c)
    t = api_time
    rtc.datetime((
        t["year"],
        t["month"],
        t["day"],
        t["weekday"],
        t["hour"],
        t["minute"],
        t["second"],
        0
    ))
    del t
    utime.sleep_ms(1000)

voltage_adc = ADC(Pin(15))
voltage_adc.atten(ADC.ATTN_11DB)
voltage_adc.width(ADC.WIDTH_12BIT)

current_adc = ADC(Pin(16))
current_adc.atten(ADC.ATTN_11DB)
current_adc.width(ADC.WIDTH_12BIT)

def get_average_voltage(adc, samples=50):
    total = 0
    for _ in range(samples):
        total += adc.read()
    avg = total / samples
    voltage = (avg / 4095) * 3.3
    return voltage
