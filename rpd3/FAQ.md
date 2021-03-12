# Klipper Log
tail -f /tmp/klippy.log

#### HW UART Setup
sudo armbian-config => enable uart3
stty -F /dev/ttyACM0
echo 111 >> /dev/ttyS3
sudo ttylog -b 115200 -d /dev/ttyS3

### INSTALL SKR V1.4 LPC1768
sudo service klipper stop
make clean
make menuconfig
# Micro-controller Architecture (LPC176x (Smoothieboard))  --->
# [*] Target board uses Smoothieware bootloader
# [ ] Use USB for communication (instead of serial)
# GPIO pins to set: !P2.3, !P0.18, !P0.16, !P0.15, !P1.0
make
./scripts/flash-sdcard.sh /dev/ttyS3 btt-skr-v1.4
sudo service klipper start

### INSTALL LINUX MCU FW
cd ~/klipper/
sudo cp "./scripts/klipper-mcu-start.sh" /etc/init.d/klipper_mcu
sudo update-rc.d klipper_mcu defaults
cd ~/klipper/
make menuconfig => Linux MCU
sudo service klipper stop
make flash
sudo service klipper start
sudo usermod -a -G tty pi

### UPGRADE !!!
sudo service klipper stop
cd ~/klipper
git pull
# ~/klipper/scripts/install-octopi.sh
make clean
make menuconfig
make
./scripts/flash-sdcard.sh /dev/ttyS3 btt-skr-v1.4
sudo service klipper start

# SKR ORIGINAL BOOTLOADER
Rename out/klipper.bin => FIRMWARE.bin 
And Put to SD and reboot SKR
# SKR betterBootloader (DFU UNLOCKED)
make flash FLASH_DEVICE=/dev/ttyS3