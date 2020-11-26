import os
import sys
from subprocess import Popen, PIPE
import fcntl
USBDEVFS_RESET= 21780

def reset(driver):
    try:
        lsusb_out = Popen("lsusb | grep -i %s" % driver, shell=True, bufsize=64, stdin=PIPE, stdout=PIPE, close_fds=True).stdout.read().strip().split()
        bus = lsusb_out[1]
        device = lsusb_out[3][:-1]
        with open(f'/dev/bus/usb/{bus.decode()}/{device.decode()}', 'w', os.O_WRONLY) as f:
            fcntl.ioctl(f, USBDEVFS_RESET, 0)
    except Exception as e:
        print(e)

if __name__ == "__main__":
    reset(sys.argv[1])
