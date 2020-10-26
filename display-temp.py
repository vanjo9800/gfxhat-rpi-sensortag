#!/usr/bin/env python

import atexit
import csv
import datetime
from math import exp
import sys
import time

# Importing socket library
import netifaces
import socket

# Import Bluetooth libraries
from bluepy.btle import BTLEException
from bluepy.sensortag import SensorTag

# Import GFX-HAT libraries
from gfxhat import touch, lcd, backlight, fonts
from PIL import Image, ImageFont, ImageDraw


# Bluetooth configuration
SENSORTAG_ADDRESS = "24:71:89:BC:4C:00"
# it takes about 4-5 seconds to obtain readings and upload to google sheets
FREQUENCY_SECONDS = 10.0


def enable_sensors(tag):
    """Enable sensors so that readings can be made."""
    tag.IRtemperature.enable()
    tag.accelerometer.enable()
    tag.humidity.enable()
    tag.magnetometer.enable()
    tag.barometer.enable()
    tag.gyroscope.enable()
    tag.keypress.enable()
    tag.lightmeter.enable()
    # tag.battery.enable()

    # Some sensors (e.g., temperature, accelerometer) need some time for initialization.
    # Not waiting here after enabling a sensor, the first read value might be empty or incorrect.
    time.sleep(1.0)


def disable_sensors(tag):
    """Disable sensors to improve battery life."""
    tag.IRtemperature.disable()
    tag.accelerometer.disable()
    tag.humidity.disable()
    tag.magnetometer.disable()
    tag.barometer.disable()
    tag.gyroscope.disable()
    tag.keypress.disable()
    tag.lightmeter.disable()
    # tag.battery.disable()


def get_readings(tag):
    """Get sensor readings and collate them in a dictionary."""
    try:
        enable_sensors(tag)
        readings = {}
        # IR sensor
        readings["ir_temp"], readings["ir"] = tag.IRtemperature.read()
        # humidity sensor
        readings["humidity_temp"], readings["humidity"] = tag.humidity.read()
        # barometer
        readings["baro_temp"], readings["pressure"] = tag.barometer.read()
        # luxmeter
        readings["light"] = tag.lightmeter.read()
        # battery
        # readings["battery"] = tag.battery.read()
        disable_sensors(tag)

        # round to 2 decimal places for all readings
        readings = {key: round(value, 2) for key, value in readings.items()}
        return readings

    except BTLEException as e:
        print("Unable to take sensor readings.")
        print(e)
        return {}


def reconnect(tag):
    try:
        tag.connect(tag.deviceAddr, tag.addrType)

    except Exception as e:
        print("Unable to reconnect to SensorTag.")
        raise e


# GFX-HAT configuration
# A squarer pixel font
# ImageFont.truetype(fonts.BitocraFull, 16)
font_old = ImageFont.truetype(fonts.AmaticSCBold, 38)
# A slightly rounded, Ubuntu-inspired version of Bitocra
font = ImageFont.truetype(fonts.BitbuntuFull, 10)


def cleanup():
    backlight.set_all(0, 0, 0)
    backlight.show()
    lcd.clear()
    lcd.show()


def get_ip():
    return netifaces.ifaddresses('wlan0')[netifaces.AF_INET][0]['addr']


def get_hostname():
    return socket.gethostname()


def main():
    print("""display-temp.py""")

    print('Connecting to {}'.format(SENSORTAG_ADDRESS))
    tag = SensorTag(SENSORTAG_ADDRESS)
    print("Connection successfull!")

    print("Initializing GFX-HAT...")
    width, height = lcd.dimensions()
    image = Image.new('P', (width, height))
    draw = ImageDraw.Draw(image)

    for x in range(6):
        touch.set_led(x, 0)
        backlight.set_pixel(x, 255, 255, 255)
        # touch.on(x, handler)

    backlight.set_all(155, 155, 155)
    backlight.show()

    atexit.register(cleanup)

    print("Reporting started every {0} seconds".format(FREQUENCY_SECONDS))
    try:
        while True:
            image.paste(0, (0, 0, width, height))

            readings = get_readings(tag)
            if not readings:
                print("SensorTag disconnected. Reconnecting.")
                reconnect(tag)
                continue

            # print readings
            print("Time:\t{}".format(datetime.datetime.now()))
            print("IR reading:\t\t{}, temperature:\t{}".format(
                readings["ir"], readings["ir_temp"]))
            print("Humidity reading:\t{}, temperature:\t{}".format(
                readings["humidity"], readings["humidity_temp"]))
            print("Barometer reading:\t{}, temperature:\t{}".format(
                readings["pressure"], readings["baro_temp"]))
            print("Luxmeter reading:\t{}".format(readings["light"]))
            fields = [datetime.datetime.now(), readings['ir'], readings['ir_temp'], readings['humidity'],
                      readings['humidity_temp'], readings['pressure'], readings['baro_temp'], readings['light']]
            with open(r'data.csv', 'a') as f:
                writer = csv.writer(f)
                writer.writerow(fields)

            # Drawing IP and Hostname
            # draw.text((2,1), "IP: " + get_ip(), 1, font)
            # draw.text((2,10), "Hostname: " + get_hostname(), 1, font)

            now = datetime.datetime.now()
            current_time = now.strftime("%H:%M:%S")
            draw.text((2, 1),  "Time      : " + str(current_time), 1, font)
            draw.text((2, 10), "IR  (temp): " +
                      str(readings["ir_temp"]) + "C", 1, font)
            draw.text((2, 20), "Hum (temp): " +
                      str(readings["humidity_temp"]) + "C", 1, font)
            draw.text((2, 30), "Bar (temp): " +
                      str(readings["baro_temp"]) + "C", 1, font)
            draw.text((2, 40), "Luxometer : " +
                      str(readings["light"]) + "lux", 1, font)
            draw.text((2, 50), "IP: " + get_ip(), 1, font)

            mean_temp = float(
                readings['ir_temp']) + float(readings['humidity_temp']) + float(readings['baro_temp'])
            mean_temp /= 3.0
            if mean_temp > 28.0:
                backlight.set_all(155, 0, 0)
            elif mean_temp > 27.0:
                backlight.set_all(155, 75, 75)
            elif mean_temp < 24.0:
                backlight.set_all(100, 100, 155)
            elif mean_temp < 23.0:
                backlight.set_all(50, 50, 155)
            elif mean_temp < 22.0:
                backlight.set_all(0, 0, 155)
            else:
                backlight.set_all(155, 155, 155)
            backlight.show()

            for x in range(width):
                for y in range(height):
                    pixel = image.getpixel((x, y))
                    lcd.set_pixel(x, y, pixel)

            lcd.show()
            # time.sleep(1.0 / 30)
            time.sleep(FREQUENCY_SECONDS)

    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
