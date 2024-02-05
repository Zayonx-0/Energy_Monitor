#! /usr/bin/env python3
#
#  Copyright (C) 2018-2022 HMS Technology Center Ravensburg GmbH, all rights reserved
#  See LICENSE.txt for more information
#                                   
"""
SimplyCAN API for Python
========================

The simplyCAN API provides a simple programming interface for the development of CAN applications 
for Windows and Linux.
"""

import sys
import os
import ctypes
from ctypes import *
from ctypes.util import find_library

DLL_VERSION_NUMBER_ERROR = -100

PY_VER = sys.version[0]
Version = "2.0.0"

dSimplyReturnValues = {
    0:   "No error occurred",
    -1:  "Unable to open the serial port",
    -2:  "Access on serial port denied",
    -3:  "Serial communication port is closed",
    -4:  "Serial communication error",
    -5:  "Command unknown on device",
    -6:  "Command response timeout reached",
    -7:  "Unexpected command response received",
    -8:  "Command response error",
    -9:  "Invalid simplyCAN protocol version",
    -10: "Invalid device firmware version",
    -11: "Invalid simplyCAN product string",
    -12: "Invalid CAN state",
    -13: "Invalid CAN baud-rate",
    -14: "Message could not be sent. TX is busy",
    -15: "API is busy",
    DLL_VERSION_NUMBER_ERROR: "Invalid DLL/SO version number",
}

class Struct(ctypes.Structure):
    def __init__(self, **kwargs):
        """
        Create an instance of class Struct.
        @param kwargs: All keyword arguments are used
                to create the struct member variables.
        """
        for item in self._fields_:
            key = item[0]
            if key in kwargs:
                setattr(self, key, kwargs[key])

    def __str__(self):
        lOut = []
        for item in self._fields_:
            key = item[0]
            if type(getattr(self, key)) is list:
                lOut.append("%s = %s" % (key, list(getattr(self, key))))
            elif type(getattr(self, key)) is int:
                lOut.append("%s = %u" % (key, getattr(self, key)))
            else:
                lOut.append("%s = %s" % (key, getattr(self, key)))
        return "\n".join(lOut)

class Identification(Struct):
    """
    Device identification message.
    """
    _fields_ = [
        ("fw_version",      c_char * 8),   # Zero terminated firmware version string e.g. "1.00.00"
        ("hw_version",      c_char * 8),   # Zero terminated hardware version string e.g. "1.00.00"
        ("product_version", c_char * 8),   # Zero terminated product version string e.g. "1.00.00"
        ("product_string",  c_char * 30),  # Zero terminated product string e.g. "simplyCAN 1.0"
        ("serial_number",   c_char * 9),   # Zero terminated serial number e.g. "HW123456"
    ]

class CanMsg(Struct):
    """
    Internal struct for CAN messages
    """
    _fields_ = [
        ("timestamp",       c_uint32),     # in milliseconds
        ("ident",           c_uint32),     # MSB=1: extended frame
        ("dlc",             c_uint8),      # MSB=1: remote frame
        ("payload",         c_uint8 * 8),   
    ]

class CanSts(Struct):
    """
    Internal struct for CAN status
    """
    _fields_ = [
        ("sts",             c_uint16),     # bit coded status flags (see CAN status definitions)
        ("tx_free",         c_uint16),     # number of free elements in CAN message tx FIFO
    ]
    def __str__(self):
        flags = ["---"] * 6
        if self.sts & 0x02:   #CAN_STATUS_RESET
            flags[4] = "RST"
        if self.sts & 0x04:   #CAN_STATUS_BUSOFF
            flags[3] = "BOF"
        if self.sts & 0x08:   #CAN_STATUS_ERRORSTATUS
            flags[2] = "ERR"                
        if self.sts & 0x10:   #CAN_STATUS_RXOVERRUN
            flags[1] = "RxO"                
        if self.sts & 0x20:   #CAN_STATUS_TXOVERRUN
            flags[1] = "TxO"     
        if self.sts & 0x40:   #CAN_STATUS_TXPENDING
            flags[0] = "PDG"
        return " ".join(flags) + "  tx_free=%u" % self.tx_free

class Message(object):
    """
    CAN messages used for reception and transmission.
    """
    def __init__(self, ident, payload=[], flags=[], timestamp=0):
        """
        Initialization of the CAN message class.
        @param ident: 11 or 29 bit CAN message identifier
        @param payload: CAN message payload
        @param flags: 'E' for extended frame, 'R' for remote frame
        @param timestamp: (optional) Timestamp of the CAN message in milliseconds
        """    
        self.timestamp = timestamp
        self.ident = ident
        self.payload = payload
        self.flags = flags
        
    def __str__(self):
        """
        Format the CAN message as string for output.
        @return: Returns the CAN message as formated string.
        """    
        payload_hex = " ".join(["%02X" % char for char in self.payload])
            
        flagstr = ""
        if 'E' in self.flags:
            flagstr += 'E'
        if 'R' in self.flags:
            flagstr += 'R'
    
        s = "%010d 0x%X %s %s" % (self.timestamp, self.ident, flagstr, payload_hex)
        return s 
        
def retrieve_serial_port():
    """
    Retrieve the first serial port with a connected simplyCAN device.
    @return: Port info as string, like 'COM3' for Windows or 'ttyACM0' for Linux or None if not available.
    """
    import serial.tools.list_ports
    
    ports = serial.tools.list_ports.grep(r"IXXAT simplyCAN")
    try:
        return ports.__next__().device
    except:
        return None
    
def is64bit():
    return ctypes.sizeof(ctypes.c_voidp) == 8
    
class SimplyCAN(object):
    """
    Class with the API
    """
    def __init__(self):
        """
        Loads the DLL/SO and initializes the API.
        """
        if os.name == "nt": # Windows
            if is64bit():
                path = os.path.join(os.path.split(__file__)[0], "simplyCAN-64.dll")
            else:
                path = os.path.join(os.path.split(__file__)[0], "simplyCAN.dll")
            self.lib = windll.LoadLibrary(path)
        else: # Linux
            path = os.path.join(os.path.split(__file__)[0], "simplyCAN.so")
            self.lib = cdll.LoadLibrary(path)
        
        # Check DLL/SO file version number
        if (c_int.in_dll(self.lib, "simply_api_version_major").value != 1 or
            c_int.in_dll(self.lib, "simply_api_version_minor").value != 1 or
            c_int.in_dll(self.lib, "simply_api_version_build").value != 1):
                return DLL_VERSION_NUMBER_ERROR
        
        self.lib.simply_open.restype = c_bool
        self.lib.simply_close.restype = c_bool
        self.lib.simply_initialize_can.restype = c_bool
        self.lib.simply_identify.restype = c_bool
        self.lib.simply_start_can.restype = c_bool
        self.lib.simply_stop_can.restype = c_bool
        self.lib.simply_reset_can.restype = c_bool
        self.lib.simply_can_status.restype = c_bool
        self.lib.simply_set_filter.restype = c_bool
        self.lib.simply_receive.restype = c_int8
        self.lib.simply_send.restype = c_bool
        self.lib.simply_get_last_error.restype = c_int16
                
    def open(self, serial_port):
        """
        Opens the serial communication interface. 
        The message filter of the CAN controller is opened for all message identifiers.
        @param serial_port: Name of the serial communication port (e.g. COM1 or /dev/ttyACM0). 
                            Use the simplyCAN bus monitor to detect on which serial COM port the 
                            simplyCAN is connected. With Windows it is also possible to use the 
                            device manager and with Linux the command "ls -l /dev/serial/by-id".
        """
        if type(serial_port) is str:
            serial_port = bytes(serial_port, "utf-8")
        return self.lib.simply_open(serial_port)
        

    def close(self):
        """
        Closes the serial communication interface and resets the CAN controller.
        @return: Return True if the function succeeded and False if an error occurred. Call get_last_error for more information.
        """
        return self.lib.simply_close()    
    
    def initialize_can(self, bitrate):
        """
        Initializes the CAN controller.
        @param bitrate: CAN bitrate as integer value, possible values: 10, 20, 50, 125, 250, 500, 800, 1000
        @return: Return True if the function succeeded and False if an error occurred. Call get_last_error for more information.
        """
        return self.lib.simply_initialize_can(bitrate)    
        
    def identify(self):
        """
        Gets firmware and hardware information about the simplyCAN device.
        @return: Return the firmware and hardware information as a struct Identification or None if an error occurred. 
                 Call get_last_error for more information.
        """
        ident = Identification()
         
        res = self.lib.simply_identify(byref(ident))
        if res:
            return ident
        return None
    
    def start_can(self):
        """
        Starts the CAN controller. Sets the CAN controller into running mode and clears the CAN
        message FIFOs. In running mode CAN messages can be transmitted and received.
        @return: Return True if the function succeeded and False if an error occurred. Call get_last_error for more information.
        """
        return self.lib.simply_start_can()
         
    def stop_can(self):
        """
        Stops the CAN controller. Sets the CAN controller into init mode. Does not reset the message
        filter of the CAN controller. Only stop the CAN controller when the CAN_STATUS_PENDING flag
        is not set.
        @return: Return True if the function succeeded and False if an error occurred. Call get_last_error for more information.
        """
        return self.lib.simply_stop_can()
         
    def reset_can(self):
        """
        Resets the CAN controller (hardware reset) and clears the message filter (open for all message
        identifiers). Sets the CAN controller into init mode.
        @return: Return True if the function succeeded and False if an error occurred. Call get_last_error for more information.
        """
        return self.lib.simply_reset_can()
         
    def can_status(self):
        """
        Gets the status of the CAN controller.
        @return: Return a pair (can_sts, tx_free) where can_sts is the CAN status as bit coded 16 bit value, and tx_free the number
                 of free elements in the CAN message tx FIFO. If an error occurred the return value is (None, None). Call get_last_error for more information.
        """
        sts = CanSts()
     
        res = self.lib.simply_can_status(byref(sts))
        if res:
            return sts
        return None
        
 
    def set_filter(self, mask, value):
        """
        Sets the 11 or 29 bit message filter of the CAN controller. To set the 29 bit message filter, the MSB in parameter value must be set.
        @param mask: 11 or 29 bit CAN message identifier mask.
        @param value: 11 or 29 bit CAN message identifier value, set MSB to set the 29 bit message filter.
        @return: Return True if the function succeeded and False if an error occurred. Call get_last_error for more information.
        """
        return self.lib.simply_set_filter(mask, value)
         
    def receive(self):
        """
        Receives a single CAN message.
        @return: Return a pair (res, can_msg) where res is the result code, and can_msg the received CAN message. If no message is available in the receive
                 queue the result code is 0 and can_msg None. If a message is available the result code is 1 and the can_msg is returned as a struct Message.
                 If an error occurred the result code is -1 and the can_msg None. Call get_last_error for more information.
        """
        msg = CanMsg()
     
        res = self.lib.simply_receive(byref(msg))
        if res == 1:
            flags = []
            size = msg.dlc & 0x7F
            id = msg.ident & 0x7FFFFFFF
            if msg.dlc & 0x80:
                flags.append('R')
                size = 1 # dlc is in first payload byte
            if msg.ident & 0x80000000:
                flags.append('E')
                 
            datalist = []
            for item in msg.payload[0:size]:
                datalist.append(item)
                 
            msg = Message(ident=id, payload=datalist, flags=flags, timestamp=msg.timestamp)
            return res, msg
        else:
            return res, None     
             
    def send(self, msg):
        """
        Writes a CAN message to the transmit FIFO. To check if the message is transmitted, request the CAN status with can_status.
        @param msg: CAN message
        @return: Return True if the function succeeded and False if an error occurred. Call get_last_error for more information.
        """
        c_msg = CanMsg()
         
        size = len(msg.payload)
        if size > 8 :
            size = 8
                 
        if 'R' in msg.flags:
            if (size > 0):
                size = msg.payload[0]
                if size > 8 :
                    size = 8
            c_msg.dlc = size | 0x80
        else:
            c_msg.dlc = size
             
        if 'E' in msg.flags:
            c_msg.ident = msg.ident | 0x80000000
        else:
            c_msg.ident = msg.ident        
        c_msg.timestamp = 0
         
        for idx, item in enumerate(msg.payload):
            c_msg.payload[idx] = item
        return self.lib.simply_send(byref(c_msg))
     
    def flush_tx_fifo(self):
        """
        Flush the tx fifo to speed up the transmission of cached CAN messages.
        """
        return self.lib.simply_flush_tx_fifo()   
         
    def get_last_error(self):
        """
        Gets the last error code (see dSimplyReturnValues). After reading the error code with get_last_error the error
        code is set to 0. Each error can only be read once.
        """
        return self.lib.simply_get_last_error()   
         
    def get_error_string(self, err_code):
        """
        Gets the error string to a related error code
        @param err_code: The received error code from get_last_error
        """
        if err_code in dSimplyReturnValues:
            return dSimplyReturnValues[err_code]
        else:
            return "Unknown error code"



