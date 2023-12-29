from enum import IntEnum

JVS_BROADCAST_ADDR  = 0xFF
JVS_HOST_ADDR       = 0x00

JVS_SYNC            = 0xE0
JVS_MARK            = 0xD0

JVS_BYTE_ESCAPES = {
	0xe0: ( 0xd0, 0xdf ),
	0xd0: ( 0xd0, 0xcf )
}

# Broadcast commands
JVS_RESET_CODE      = 0xF0
JVS_SETADDR_CODE    = 0xF1
JVS_COMCHG_CODE     = 0xF2
# Init commands
JVS_IOIDENT_CODE    = 0x10
JVS_CMDREV_CODE     = 0x11
JVS_JVSREV_CODE     = 0x12
JVS_COMVER_CODE     = 0x13
JVS_FEATCHK_CODE    = 0x14
JVS_MAINID_CODE     = 0x15
# Data I/O commands
JVS_READSWITCH_CODE     = 0x20
JVS_READCOIN_CODE       = 0x21
JVS_READANALOG_CODE     = 0x22
JVS_READROTARY_CODE     = 0x23
JVS_READKEY_CODE        = 0x24
JVS_READSCREENPOS_CODE  = 0x25
JVS_READMISC_CODE       = 0x26
# Output commands
JVS_READPAYOUT_CODE     = 0x2E
JVS_DATARETRY_CODE      = 0x2F
JVS_COINDECREASE_CODE   = 0x30
JVS_PAYOUTINCREASE_CODE = 0x31
JVS_GENERICOUT1_CODE    = 0x32
JVS_ANALOGOUT_CODE      = 0x33
JVS_CHARACTEROUT_CODE   = 0x34
JVS_COININCREASE_CODE   = 0x35
JVS_PAYOUTDECREASE_CODE = 0x36
JVS_GENERICOUT2_CODE    = 0x37        # Sega Type 1 IO does not support this command
JVS_GENERICOUT3_CODE    = 0x38        # Sega Type 1 IO does not support this command

# Commands = 0x60 to = 0x7F are manufacturer specific and not covered here

# Status code
class JVS_StatusCodes(IntEnum):
    JVS_STATUS_NORMAL           = 1
    JVS_STATUS_UNKNOWNCMD       = 2       # Sega IO sends this if there is a parameter error
    JVS_STATUS_CHECKSUMERROR    = 3
    JVS_STATUS_OVERFLOW         = 4       # Sega IO sends this back when it receives a empty packet

# Report codes
class JVS_ReportCodes(IntEnum):
    JVS_REPORT_NORMAL           = 1
    JVS_REPORT_PARAMETERERROR   = 2
    JVS_REPORT_DATAERROR        = 3
    JVS_REPORT_BUSY             = 4

# Coin Condition codes
class JVS_CoinCodes(IntEnum):
    JVS_COIN_NORMAL             = 0
    JVS_COIN_JAM                = 1
    JVS_COIN_NOCOUNTER          = 2
    JVS_COIN_BUSY               = 3

# JVS Feature list (for use with jvs_message):
# These are actually in BCD format which isnt mentioned for some reason
class JVS_FeatureCodes(IntEnum):
    JVS_FEATURE_END         = 0
    JVS_FEATURE_SWITCH      = 1
    JVS_FEATURE_COIN        = 2
    JVS_FEATURE_ANALOG      = 3
    JVS_FEATURE_ROTARY      = 4
    JVS_FEATURE_KEYCODE     = 5
    JVS_FEATURE_SCREEN      = 6
    JVS_FEATURE_MISC        = 7
    JVS_FEATURE_CARD        = 10
    JVS_FEATURE_MEDAL       = 11
    JVS_FEATURE_GPO         = 12
    JVS_FEATURE_ANALOG_OUT  = 13
    JVS_FEATURE_CHARACTER   = 14
    JVS_FEATURE_BACKUP      = 15

# JVS character output types (for use with jvs_message):
class JVS_CharaOutputTypes(IntEnum):
    JVS_CHARACTER_NONE      = 0
    JVS_CHARACTER_ASCII     = 1
    JVS_CHARACTER_ALPHA     = 2
    JVS_CHARACTER_KATA      = 3
    JVS_CHARACTER_KANJI     = 4

def bcd2dec(bcd):
    return (((bcd & 0xf0) >> 4) * 10 + (bcd & 0x0f))

def DEC2BCD(dec):
    tens, units = divmod(dec, 10)
    return (tens << 4) + units