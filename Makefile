#---------------------------------------------------------------------------------------------------------------------
# Feelo — GBA wellness check-in tracker, built with Butano.
# See third_party/butano/template/Makefile for the documentation of every variable.
#
# Toolchain: either devkitARM (DEVKITARM env var) or Wonderful Toolchain
# (WONDERFUL_TOOLCHAIN env var, e.g. ~/wonderful) must be installed;
# butano.mak auto-detects whichever is present, preferring devkitARM.
#---------------------------------------------------------------------------------------------------------------------
TARGET      	:=  feelo
BUILD       	:=  build
LIBBUTANO   	:=  third_party/butano/butano
PYTHON      	:=  $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
SOURCES     	:=  src
INCLUDES    	:=  include
DATA        	:=
GRAPHICS    	:=  graphics
AUDIO       	:=  audio
AUDIOBACKEND	:=  maxmod
AUDIOTOOL		:=
DMGAUDIO    	:=  dmg_audio
DMGAUDIOBACKEND	:=  default
ROMTITLE    	:=  FEELO
ROMCODE     	:=  2FLO
USERFLAGS   	:=  -DBN_CFG_SPRITE_TILES_MAX_ITEMS=256
USERCXXFLAGS	:=
USERASFLAGS 	:=
USERLDFLAGS 	:=
USERLIBDIRS 	:=
USERLIBS    	:=
DEFAULTLIBS 	:=
STACKTRACE		:=
USERBUILD   	:=
EXTTOOL     	:=

#---------------------------------------------------------------------------------------------------------------------
# Export absolute butano path:
#---------------------------------------------------------------------------------------------------------------------
ifndef LIBBUTANOABS
	export LIBBUTANOABS	:=	$(realpath $(LIBBUTANO))
endif

#---------------------------------------------------------------------------------------------------------------------
# Include main makefile:
#---------------------------------------------------------------------------------------------------------------------
include $(LIBBUTANOABS)/butano.mak
