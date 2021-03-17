### MCP23017 OLED Controller
# OLED 1.3 I2C 0x3C
# MCP23017 i2C 0x20
# PORT   A0  A1  A2  A3  A4  A5  A6   A7  |  B0  B1  B2  B3  B4  B5  B6   B7
# FUNC   K4  K5  K6  K7  K8  L4  K11  L5  |  K1  L1  K2  K3  L2  K9  K10  L3
# IN     1  1  1  1  1   1   0   1    0   |  1   0   1   1   0   1   1    0
# OUT    0   0   0   0   0   1   0    1   |  0   1   0   0   1   0   0    1
# PIN    0   1   2   3   4   5   6    7      8   9   10  11  12  13  14   15

I2C_BUS = 0
MCP23017_ADDR = 0x20
OLED_ADDR = 0x3c

# MCP23017 Registers
IODIRA = 0x00       # IN/OUT PA
IODIRB = 0x01       # IN/OUT PA
GPINTENA = 0x04     # INT PA
GPINTENB = 0x05     # INT PB
DEFVALA = 0
DEFVALB = 0x07
INTCONA = 0x08
INTCONB = 0x09
IOCON = 0x0A 
GPPUA = 0x0C        # PulUp PA
GPPUB = 0x0D        # PulUp PB
INTFA = 0x0E
INTFB = 0x0F
INTCAPA = 0x10
INTCAPB = 0x11
GPIOA = 0x12        # State PA
GPIOB = 0x13        # State PB
OLATA = 0x14
OLATB = 0x15

# 0xFF (11111111) - INPUT
# 0x00 (00000000) - OUTPUT

i2cdetect -y 0              # Get all devices on BUS 0
i2cget -y 0 0x20 0x00       # Get PORTA Mode
i2cget -y 0 0x20 0x01       # Get PORTB Mode

# Get PA PB Mode
i2cget -y 0 0x20 0x00 && i2cget -y 0 0x20 0x01
# Get PA PB State
i2cget -y 0 0x20 0x12 && i2cget -y 0 0x20 0x13

i2cset -y 0 0x20 0x00 0xFF              # SET ALL INPUTS PORTA

# Ports for INPUT/OUT
# PA         PB    
# 1111 1010  1011 0110
# 
i2cset -y 0 0x20 0x00 $(( 2#01011111 )) # SET PA INPUTS 11111010  A5 A7    - OUT(LEDS)
i2cset -y 0 0x20 0x01 $(( 2#01101101 )) # SET PB INPUTS 10110110  B1 B4 B7 - OUT(LEDS)
i2cset -y 0 0x20 0x00 0x5f              # SET PA IN in HEX
i2cset -y 0 0x20 0x01 0x6d              # SET PB IN in HEX
# Ports PulUps
i2cset -y 0 0x20 0x0C 0x5f              # SET PULUP A KEYS
i2cset -y 0 0x20 0x0D 0x6d              # SET PULUP B KEYS
# INT MIRROR & INTPOLUP
i2cset -y 0 0x20 0x0A $(( 2#01000010 ))
i2cset -y 0 0x20 0x0A # 0x42


###  OLED CONTROLLER  ###
#------- MCP23017 ------#
#
# LED1 LED2 LED3 LED4 LED5
# 9    12   15   5    7  
# KEY1 KEY2 KEY3 KEY4 KEY5 KEY6 KEY7 KEY8 KEY9 KEY10 KEY11
# 8    10   11   0    1    2    3    4    13   14    6


# SET INPUT(KEYS) / OUT(LED)
i2cset -y 0 0x20 0x00 0x5f && i2cset -y 0 0x20 0x01 0x6d
# KEYS PULUP
i2cset -y 0 0x20 0x0C 0x5f && i2cset -y 0 0x20 0x0D 0x6d
# LED OFF
i2cset -y 0 0x20 0x12 0x5f && i2cset -y 0 0x20 0x13 0x6d
# Disable Interrupt
i2cset -y 0 0x20 0x04 0x00 && i2cset -y 0 0x20 0x05 0x00

## LEDs test
# COLOR: Blue Red  Blue Green Yellow
# NUM:   LED1 LED2 LED3 LED4  LED5
# PORT:  B1   B4   B7   A5    A7
# OFF:   0x6d           0x5f 
# ON:    0x6f 0x7d 0xed 0x5f  0xdf
i2cset -y 0 0x20 0x13 $(( 2#01101111 )) && i2cget -y 0 0x20 0x13 # LED1 ON BLUE
i2cset -y 0 0x20 0x13 0x6f # LED1 ON BLUE
i2cset -y 0 0x20 0x13 0x7d # LED2 ON RED
i2cset -y 0 0x20 0x13 0xed # LED3 ON BLUE
i2cset -y 0 0x20 0x12 0x7f # LED4 ON GREEN
i2cset -y 0 0x20 0x12 0xdf # LED5 ON YELLOW
# ALL LED OFF (Init State)
i2cset -y 0 0x20 0x12 0x5f && i2cset -y 0 0x20 0x13 0x6d

### WiringPi Metod ###
######################

# mcp23017:[Base]:[i2c addr]
gpio -x mcp23017:100:0x20 mode 109 out
gpio -x mcp23017:100:0x20 write 109 1
gpio -x mcp23017:100:0x20 write 109 0


# Define Leds & Keys Arrays
leds=(109 112 115 105 107)
keys=(108 110 111 100 101 102 103 104 113 114 106)

# LED Test
for led in ${leds[@]}; do
  gpio -x mcp23017:100:0x20 $led 1
  sleep 1
  gpio -x mcp23017:100:0x20 $led 0
done

