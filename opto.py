#!/usr/bin/env python
# -*- coding: utf-8 -*-

import serial
import time
from ctypes import c_ushort


class Opto(object):
    def __init__(self, port=None):
        self.port = port
        self.crc_table = self._init_crc_table()
        self.ser = None
        self._current = None
        self._current_max = 292.84

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close(soft_close=False)

    def connect(self):
        """
        Open the serial port and connect
        """
        self.ser = serial.Serial()
        self.ser.baudrate = 115200
        self.ser.port = self.port
        self.ser.timeout = 0.2
        try:
            self.ser.open()
            if self.handshake() != b'Ready\r\n':
                raise(serial.SerialException('Handshake failed'))
        except serial.SerialException:
            self.ser.close()
            raise

    def close(self, soft_close=None):
        """
        Close the serial port

        Args:
            soft_close (bool): Step-down the current and set to 0 before close.
        """
        if soft_close is None:
            soft_close = False
        if self.ser:
            if self._current and soft_close:
                for f in range(5):
                    self._current = self.current(self._current/2)
                    time.sleep(0.100)
                self.current(0)
            self.ser.close()
            del(self.ser)

    def _send_cmd(self, cmd, include_crc=None, wait_for_resp=None):
        """
        Send a command

        Args:
            include_crc (bool): Append a CRC to the end of the command.
            wait_for_resp (bool): Return the response of the Optotune.

        Returns:
            Optotune response, if wait_for_response is True. Otherwise, None.
        """
        if include_crc is None:
            include_crc = True
        if wait_for_resp is None:
            wait_for_resp = True
        if self.ser is None:
            raise(serial.SerialException('Serial not connected'))
        if include_crc:
            crc = self.calc_crc(cmd)
            self.ser.write(cmd+crc)
        else:
            self.ser.write(cmd)
        if wait_for_resp:
            resp = self.ser.read_until('\r\n')
            if include_crc:
                resp_crc = resp[-4:-2]
                resp_content = resp[:-4]
                if resp_crc != self.calc_crc(resp_content):
                    raise(serial.SerialException(
                        'CRC mismatch: {}'.format(resp)))
            else:
                resp_content = resp
            if resp_content[0] == b'E':
                raise(serial.SerialException(
                    'Command error: {}').format(resp_content))
            return resp_content

    def calc_crc(self, data):
        """
        Calculate a CRC
        """
        crc = 0
        for d in data:
            tmp = crc ^ d
            crc = (crc >> 8) ^ self.crc_table[(tmp & 0x00ff)]
        return crc.to_bytes(2, byteorder='little')

    def _init_crc_table(self, polynomial=None):
        """
        Initialize the lookup table for CRC calculation
        """
        if polynomial is None:
            polynomial = 0xA001
        table = []
        for i in range(0, 256):
            crc = c_ushort(i).value
            for j in range(0, 8):
                if crc & 0x0001:
                    crc = c_ushort(crc >> 1).value ^ polynomial
                else:
                    crc = c_ushort(crc >> 1).value
            table.append(crc)
        return table

    def handshake(self):
        """
        Return 'start' to confirm connection (ID #0101)
        """
        r = self._send_cmd(b'Start', include_crc=False)
        return r

    def firmwaretype(self):
        """
        Return firmware type (ID #0103)
        """
        r = self._send_cmd(b'H')
        self._firmwaretype = r[1]
        return self._firmwaretype

    def firmwarebranch(self):
        """
        Return firmware branch (ID #0104)
        """
        r = self._send_cmd(b'F')
        self._firmwarebranch = r[1]
        return self._firmwarebranch

    def partnumber(self):
        """
        Return part number (ID #0105)
        """
        r = self._send_cmd(b'J')
        self._partnumber = r[1:4]
        return self._partnumber

    def current_upper(self, value=None):
        """
        Get/set upper software current limit (ID #0402)

        Args:
            value (float): Set current in mA, None returns current value

        Returns:
            The upper software current limit
        """
        if value is None:
            r = self._send_cmd(b'CrUA\x00\x00')
        else:
            if value > self._current_max:
                raise(ValueError(
                    'Limit cannot be higher than the maximum output current.'))
            data = int(value * 4095/self._current_max)
            data = data.to_bytes(2, byteorder='big', signed=True)
            r = self._send_cmd(b'CwUA'+data)
        self._current_upper = (int.from_bytes(r[3:5], byteorder='big') *
                               self._current_max/4095)
        return self._current_upper

    def current_lower(self, value=None):
        """
        Get/set lower software current limit (ID #0403)

        Args:
            value (float): Set current in mA, None returns current value

        Returns:
            The lower software current limit
        """
        if value is None:
            r = self._send_cmd(b'CrLA\x00\x00')
        else:
            if value > self._current_max:
                raise(ValueError(
                    'Limit cannot be higher than the maximum output current.'))
            data = int(value*4095/self._current_max)
            data = data.to_bytes(2, byteorder='big', signed=True)
            r = self._send_cmd(b'CwLA'+data)
        self._current_lower = (int.from_bytes(r[3:5], byteorder='big') *
                               self._current_max/4095)
        return self._current_lower

    def firmwareversion(self):
        """
        Return the firmware version (ID #0701)

        Returns:
            Major Revison, Minor Revision, Build and Revison
        """
        r = self._send_cmd(b'V')
        self._firmwarerevision = '{}.{}.{}.{}'.format(
            r[1],
            r[2],
            int.from_bytes(r[3:5], byteorder='big'),
            int.from_bytes(r[4:7], byteorder='big'))
        return self._firmwarerevision

    def deviceid(self):
        """
        Return device ID (ID #0901)
        """
        r = self._send_cmd(b'IR\x00\x00\x00\x00\x00\x00\x00\x00')
        self._deviceid = r[2:]
        return self._deviceid

    def gain(self, value=None):
        """
        Get/set the gain variable for focal power drift compensation (ID #1100)

        Returns:
            Focal power range at the given temperature limits and given gain
            variable as tuple if the gain is set. Otherwise, getting with no
            value (value=Null) returns the gain value.

        Todo:
            Test
        """
        if value is None:
            r = self._send_cmd(b'Or\x00\x00')
            self._gain = int.from_bytes(r[2:], byteorder='big')/100
            return self._gain
        else:
            if value < 0 or value > 5:
                raise(ValueError('Gain must be between 0 and 5.'))
            data = int(value*100)
            data = data.to_bytes(2, byteorder='big', signed=False)
            r = self._send_cmd(b'Ow'+data)
            status = r[2]
            # XYZ: CHECK VERSION
            focal_max = (int.from_bytes(r[3:5], byteorder='big')/200)-5
            focal_min = (int.from_bytes(r[5:7], byteorder='big')/200)-5
            return (status, focal_max, focal_min)

    def serialnumber(self):
        """
        Return serial number (ID #0102)
        """
        r = self._send_cmd(b'X')
        self._serialnumber = r[1:]
        return self._serialnumber

    def current(self, value=None):
        """
        Get/set current (ID #0201)

        Args:
            value (float): Set current in mA, None returns current value

        Returns:
            The current
        """
        if value is None:
            r = self._send_cmd(b'Ar\x00\x00')
            self._current = (int.from_bytes(r[1:], byteorder='big',
                             signed=True) * self._current_max/4095)
        else:
            data = int(value*4095/self._current_max)
            data = data.to_bytes(2, byteorder='big', signed=True)
            r = self._send_cmd(b'Aw'+data, wait_for_resp=False)
            self._current = value
        return self._current

    def siggen_upper(self, value=None):
        """
        Get/set signal generator upper current swing limit (ID #0305)

        Args:
            value (float): Set current in mA, None returns current value

        Returns:
            The upper current swing limit

        Todo:
            Test
        """
        if value is None:
            r = self._send_cmd(b'PrUA\x00\x00\x00\x00')
            self._siggen_upper = (int.from_bytes(r[3:5], byteorder='big',
                                  signed=True) * self._current_max/4095)
        else:
            data = int(value*4095/self._current_max)
            data = data.to_bytes(2, byteorder='big', signed=True)
            r = self._send_cmd(b'PwUA'+data+b'\x00\x00', wait_for_resp=False)
            self._siggen_upper = value
        return self._siggen_upper

    def siggen_lower(self, value=None):
        """
        Get/set signal generator lower current swing limit (ID #0306)

        Args:
            value (float): Set current in mA, None returns current value

        Returns:
            The lower current swing limit

        Todo:
            Test
        """
        if value is None:
            r = self._send_cmd(b'PrLA\x00\x00\x00\x00')
            self._siggen_lower = (int.from_bytes(r[3:5], byteorder='big',
                                  signed=True) * self._current_max/4095)
        else:
            data = int(value*4095/self._current_max)
            data = data.to_bytes(2, byteorder='big', signed=True)
            r = self._send_cmd(b'PwLA'+data+b'\x00\x00', wait_for_resp=False)
            self._siggen_lower = value
        return self._siggen_lower

    def siggen_freq(self, value=None):
        """
        Get/set signal generator frequency (ID #0307)

        Args:
            value (float): Set frequency in Hz, None returns current value

        Returns:
            The signal generator frequency

        Todo:
            Test
        """
        if value is None:
            r = self._send_cmd(b'PrFA\x00\x00\x00\x00')
            self._siggen_freq = int.from_bytes(r[3:7], byteorder='big')
        else:
            data = int(value*1000)
            data = data.to_bytes(4, byteorder='big', signed=False)
            r = self._send_cmd(b'PwFA'+data, wait_for_resp=False)
            self._siggen_freq = value
        return self._siggen_freq

    def temp_limits(self, value=None):
        """
        Get/set the upper and lower temperature limits to channel A (ID #0309)

        Returns:
            The achievable focal power range at the given temperature.

        Todo:
            Better implement and test
        """
        if value is None:
            r = self._send_cmd(b'PrTA\x00\x00\x00\x00')
            return (int.from_bytes(r[5:7], byteorder='big', signed=True)/200 - 5,
                    int.from_bytes(r[3:5], byteorder='big', signed=True)/200 - 5)
        else:
            if value[0] > value[1]:
                raise(ValueError)
            data = ((value[1]*16).to_bytes(2, byteorder='big', signed=True) +
                    (value[0]*16).to_bytes(2, byteorder='big', signed=True))
            r = self._send_cmd(b'PwTA'+data)
            return (int.from_bytes(r[5:7], byteorder='big', signed=True)/200 - 5,
                    int.from_bytes(r[3:5], byteorder='big', signed=True)/200 - 5)

    def focalpower(self, value=None):
        """
        Get/set focal power (ID #0310)

        Args:
            value (float): Set frequency in diopters, None return current value

        Returns:
            The focal power

        Todo:
            Fix return format
        """
        if value is None:
            r = self._send_cmd(b'PrDA\x00\x00\x00\x00')
            self._focalpower = (int.from_bytes(r[2:4], byteorder='big',
                                signed=True)/200 - 5)
        else:
            # XYZ: CHECK VERSION
            data = int((value+5)*200)
            data = data.to_bytes(2, byteorder='big', signed=True)
            self._send_cmd(b'PwDA'+data+b'\x00\x00')
            self._focalpower = value
        return self._focalpower

    def current_max(self, value=None):
        """
        Get/set maximum firmware output current (ID #0401)

        Args:
            value (float): Set current in mA, None returns current value

        Returns:
            The maximum firmware output current
        """
        if value is None:
            r = self._send_cmd(b'CrMA\x00\x00')
            self._current_max = (int.from_bytes(r[3:5], byteorder='big',
                                 signed=True)/100)
        else:
            if value > 292.84:
                value = 292.84
            data = int(value*100)
            data = data.to_bytes(2, byteorder='big', signed=True)
            self._send_cmd(b'CwMA'+data)
            self._current_max = value
        return self._current_max

    def temp_reading(self):
        """
        Return lens temperature (ID #0501)
        """
        r = self._send_cmd(b'TCA')
        self._temp_reading = (int.from_bytes(r[3:5], byteorder='big',
                              signed=True) * 0.0625)
        return self._temp_reading

    def get_status(self):
        """
        Return firmware status information (ID #0503)
        """
        r = self._send_cmd(b'Sr')
        self._status = r[1:]
        return self._status

    def eeprom_read(self, value):
        """
        Read byte from EEPROM (ID #0609)

        Args:
            value (byte): Address

        Returns:
            Byte read

        Todo:
            Test
        """
        data = int(value).to_bytes(1, byteorder='big', signed=True)
        r = self._send_cmd(b'Zr'+data)
        return r[1]

    def analog_input(self):
        """
        Return analog reading (ID #1001)

        Todo:
            Test
        """
        r = self._send_cmd(b'GAA')
        return int.from_bytes(r[3:5], byteorder='big', signed=False)

    def eeprom_write(self, address, value):
        """
        Write byte to EEPROM (ID #9998)

        Args:
            address (byte): Address
            value (byte): Byte to be written

        Returns:
            Byte written

        Todo:
            Test
        """
        data_a = int(address).to_bytes(1, byteorder='big', signed=True)
        data_b = int(value).to_bytes(1, byteorder='big', signed=True)
        r = self._send_cmd(b'Zw'+data_a+data_b)
        return r[1]

    def eeprom_contents(self):
        """
        Dump contents of EEPROM (ID #9999)

        Todo:
            Test
        """
        r = self._send_cmd(b'D\x00\x00')
        return r[1:]

    def mode(self, mode_str=None):
        """
        Get/set operation mode (ID #0301, 0302, 0303, 0304, 0308, 0321)

        Args:
            mode_str (str): Mode ['sinusoidal', 'rectangular', 'current',
                                  'triangular', 'focal','analog']

        Returns:
            Current operation mode as a string
        """
        if mode_str is None:
            modes = {1: 'current',
                     2: 'sinusoidal',
                     3: 'triangular',
                     4: 'rectangular',
                     5: 'focal',
                     6: 'analog',
                     7: 'position'}
            r = self._send_cmd(b'MMA')
            self._mode = modes[r[3]]
        else:
            if mode_str == 'sinusoidal':        # ID #0301
                self._send_cmd(b'MwSA')
            elif mode_str == 'rectangular':     # ID #0302
                self._send_cmd(b'MwQA')
            elif mode_str == 'current':         # ID #0303
                self._send_cmd(b'MwDA')
            elif mode_str == 'triangular':      # ID #0304
                self._send_cmd(b'MwTA')
            elif mode_str == 'focal':           # ID #0308
                self._send_cmd(b'MwCA')
            elif mode_str == 'analog':          # ID #0321
                self._send_cmd(b'MwAA')
            else:
                raise(ValueError('{}'.format(mode_str)))
            self._mode = mode_str
        return self._mode
