#!/bin/bash

#------------------------------------------#
###           OLED CONTROLLER            ###
#
# Power button Event handler
# For klipper WakeUp
#------------------------------------------#

LED_FILAMENT_PIN="109"
LED_PWR_PIN="112"
LED_FAN_PIN="115"
LED_PAUSE_PIN="105"
LED_PRINT_PIN="107"
BTN_UP=1
BTN_FILAMENT=1
BTN_DOWN=1
BTN_1=1
BTN_2=1
BTN_3=1
BTN_4=1
BTN_5=1
BTN_PWR=1
BTN_FAN=1
BTN_PAUSE=1

# MCP23017 Registers
IODIRA=0x00
IODIRB=0x01
GPINTENA=0x04
GPINTENB=0x05
DEFVALA=0x06
DEFVALB=0x07
INTCONA=0x08
INTCONB=0x09
IOCON=0x0A
GPPUA=0x0C
GPPUB=0x0D
INTFA=0x0E
INTFB=0x0F
INTCAPA=0x10
INTCAPB=0x11
GPIOA=0x12
GPIOB=0x13
OLATA=0x14
OLATB=0x15

reset_mcp(){
    for addr in {0..22}; do
        if [ $addr -eq 0 ] || [ $addr -eq 1 ]; then
            # All port as INPUT
            i2cset -y 0 0x20 $addr 0xff
        else
            i2cset -y 0 0x20 $addr 0x00
        fi
    done
}

read_mcp(){
    for addr in {0..22}; do
        data=$(i2cget -y 0 0x20 $addr)
        echo "$addr : $data"
    done
}

init_mcp() {


    # Keys - IN Leds - OUT
    # i2cset -y 0 0x20 0x00 $((2#01011111)) # 11111010  A5 A7    - OUT(LEDS)
    # i2cset -y 0 0x20 0x01 $((2#01101101)) # 10110110  B1 B4 B7 - OUT(LEDS)
    i2cset -y 0 0x20 $IODIRA 0x5f
    i2cset -y 0 0x20 $IODIRB 0x6d
    # Keys PulUps
    i2cset -y 0 0x20 $GPPUA 0x5f
    i2cset -y 0 0x20 $GPPUB 0x6d
    # Leds OFF
    # i2cset -y 0 0x20 $GPIOA 0x5f
    # i2cset -y 0 0x20 $GPIOB 0x6d
    ## Interrupt
    # i2cset -y 0 0x20 $IOCON 0x40
    # i2cset -y 0 0x20 $INTCONA 0x5f 
    # i2cset -y 0 0x20 $INTCONB 0x6d
    # i2cset -y 0 0x20 $DEFVALA 0x5f 
    # i2cset -y 0 0x20 $DEFVALB 0x6d
    # i2cset -y 0 0x20 $GPINTENA 0x5f 
    # i2cset -y 0 0x20 $GPINTENB 0x6d
}

set_led(){
  # set_led [LED_NAME] [1|0]
  gpio -x mcp23017:100:0x20 write $1 $2  
}

read_buttons(){
    # GPIOA=$(i2cget -y 0 0x20 0x12)
    # GPIOB=$(i2cget -y 0 0x20 0x13)
    # INTFA=$(i2cget -y 0 0x20 0x0E)
    # INTFB=$(i2cget -y 0 0x20 0x0F)

    # btn_pins=(108 110 111 100 101 102 103 104 113 114 106)
    # for btn_pin in ${btn_pins[@]}; do
    #     btn_state[$btn_pin]=`gpio -x mcp23017:100:0x20 read $btn_pin`
    # done

    BTN_UP=$(gpio -x mcp23017:100:0x20 read 108)
    BTN_FILAMENT=$(gpio -x mcp23017:100:0x20 read 110)
    BTN_DOWN=$(gpio -x mcp23017:100:0x20 read 111)
    BTN_1=$(gpio -x mcp23017:100:0x20 read 100)
    BTN_2=$(gpio -x mcp23017:100:0x20 read 101)
    BTN_3=$(gpio -x mcp23017:100:0x20 read 102)
    BTN_4=$(gpio -x mcp23017:100:0x20 read 103)
    BTN_5=$(gpio -x mcp23017:100:0x20 read 104)
    BTN_PWR=$(gpio -x mcp23017:100:0x20 read 113)
    BTN_FAN=$(gpio -x mcp23017:100:0x20 read 114)
    BTN_PAUSE=$(gpio -x mcp23017:100:0x20 read 106)

    if [ $BTN_FILAMENT -eq 0 ]; then
        set_led $LED_FILAMENT_PIN 1
    else
        set_led $LED_FILAMENT_PIN 0 
    fi
    if [ $BTN_PWR -eq 0 ]; then
        set_led $LED_PWR_PIN 1
    else
        set_led $LED_PWR_PIN 0
    fi
    if [ $BTN_FAN -eq 0 ]; then
        set_led $LED_FAN_PIN 1
    else
        set_led $LED_FAN_PIN 0
    fi
    if [ $BTN_PAUSE -eq 0 ]; then
        set_led $LED_PAUSE_PIN 1
    else
        set_led $LED_PAUSE_PIN 0
    fi
}

send_gcode(){
    echo "$1"> /tmp/printer
}

printer_sleep(){
    # echo "Printer go to sleep"
    # send_gcode "M118 Go to sleep"
    sudo service klipper stop
    sudo service klipper_mcu stop
    sleep 3
    # OFF PSU Power
    gpio write 25 0
    # OFF OLED Display             
    i2cset -y 0 0x3c 0x00 0xAE
    # OFF oled_controller Leds
    i2cset -y 0 0x20 0x12 0x5f && i2cset -y 0 0x20 0x13 0x6d
    # OFF PWR LED
    # pwr_led 0
    # wall Printer Zzzz..
}

printer_wakeup(){
    # echo "Printer WakeUp Event"
    PSU_POWER=$(gpio read 25)
    KLIPPER=$(pgrep klipper && echo 1)
    KLIPPER_MCU=$(pgrep klipper_mcu && echo 1)

    if [ -n $PSU_POWER ]
    then
        # echo PSU ON
        gpio write 25 1
    fi
    sleep 1
    if [ $KLIPPER_MCU ]
    then
        # echo Restart klipper_mcu.service
        sudo service klipper_mcu restart
    else
        # echo Start klipper_mcu.servicer
        sudo service klipper_mcu start
    fi
    sleep 1
    if [ $KLIPPER ]
    then
        # echo Restart klipper.service active
        sudo service klipper restart
    else
        # echo Start klipper.service
        sudo service klipper start
    fi
    sleep 2
    # ON OLED Display 
    i2cset -y 0 0x3c 0x00 0xAF
    # wall Printer Redy
    exit 0
}

system_shutdown(){
    # System shutdow after 1min
    sudo shutdown -h +1
    exit 0
}

if [ "$1" = "wakeup" ]; then
    printer_wakeup
elif [ "$1" = "shutdown" ]; then
    system_shutdown
elif [ "$1" = "reset" ]; then
    reset_mcp
    #init_mcp
    exit 0
elif [ "$1" = "read" ]; then
    read_mcp
    exit 0
elif [ "$1" = "sleep" ]; then
    printer_sleep
    exit 0
elif [ "$1" = "" ]; then
    # Stop Klipper
    # printer_sleep
    # oled_controller event handler
    while true; do
        read_buttons
        if [ $BTN_FAN -eq 0 ]; then
            # System Shutdown
            if [ $BTN_PWR -eq 0 ]; then
                system_shutdown
            fi
        fi
        # Power button event
        if [ $BTN_PWR -eq 0 ]; then
            printer_wakeup
        fi
        sleep 1
    done
fi

