### OLED CONTROLLER ###
#------- --------------#

#!/bin/sh

# MCP23017 Registers
# IODIRA = 0x00       # IN/OUT PA
# IODIRB = 0x01       # IN/OUT PA
# GPINTENA = 0x04     # INT PA
# GPINTENB = 0x05     # INT PB
# DEFVALA = 0x06
# DEFVALB = 0x07
# INTCONA = 0x08
# INTCONB = 0x09
# IOCON = 0x0A 
# GPPUA = 0x0C        # PulUp PA
# GPPUB = 0x0D        # PulUp PB
# INTFA = 0x0E
# INTFB = 0x0F
# INTCAPA = 0x10
# INTCAPB = 0x11
# GPIOA = 0x12        # State PA
# GPIOB = 0x13        # State PB
# OLATA = 0x14
# OLATB = 0x15

# 0xFF (11111111) - ALL INPUT
# 0x00 (00000000) - ALL OUTPUT

GPIOA=$(i2cget -y 0 0x20 0x12)
GPIOB=$(i2cget -y 0 0x20 0x13)

## INIT MCP23017 
# Keys - IN Leds - OUT
# i2cset -y 0 0x20 0x00 $((2#01011111)) # 11111010  A5 A7    - OUT(LEDS)
# i2cset -y 0 0x20 0x01 $((2#01101101)) # 10110110  B1 B4 B7 - OUT(LEDS)
i2cset -y 0 0x20 0x00 0x5f
i2cset -y 0 0x20 0x01 0x6d
# Keys PulUps
i2cset -y 0 0x20 0x0C 0x5f
i2cset -y 0 0x20 0x0D 0x6d
# Leds OFF
i2cset -y 0 0x20 0x12 0x5f
i2cset -y 0 0x20 0x13 0x6d

## Interrupt
# Enable for Keys
i2cset -y 0 0x20 0x04 0x5f 
i2cset -y 0 0x20 0x05 0x6d
# Mirror INTA INTB
i2cset -y 0 0x20 0x0A 0x40
# Mirror and PolUp INTA INTB
# i2cset -y 0 0x20 0x0A 0x42

sleep 1

echo "INIT MCP23017"
echo "GPIOA:$GPIOA GPIOB:$GPIOB"
