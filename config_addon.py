# -*- coding: utf-8 -*-
# Copyright: (C) kaiu <https://github.com/AndreyKaiu>
# License: GNU GPL version 3 or later <https://www.fsf.org/>
# Version 1.0, date: 2026-01-02
""" addon configuration """

from aqt import mw
import anki.lang
from aqt.utils import (showText, showInfo, tooltip) 

# ========================= CONFIG ============================================
# Loading the add-on configuration
config = mw.addonManager.getConfig(__name__)
meta  = mw.addonManager.addon_meta(__name__)
this_addon_provided_name = meta.provided_name

def config_f(par1, par2, default=""):
    """get data from config"""
    try:
        ret = config[par1][par2]
        return ret
    except Exception as e:        
        print("ERROR config_f(): ", e)
        return default     

language_name = config_f("GLOBAL_SETTINGS", "language", "en")
current_language = anki.lang.current_lang #en, pr-BR, en-GB, ru and the like
if not language_name: # if you need auto-detection     
    language_name = current_language
    if language_name not in config["LOCALIZATION"]:        
        language_name = "en" # If it is not supported, we roll back to English               
    
try:
    localization = config["LOCALIZATION"][language_name]
except Exception as e:
    text = f"ERROR in add-on '{this_addon_provided_name}'\n"
    text += f"Config[\"GLOBAL_SETTINGS\"][\"language\"] does not contain '{language_name}'"
    text += "\nChange the add-on configuration, \"language\": \"en\""
    language_name = "en"
    config["GLOBAL_SETTINGS"]["language"] = language_name # change language
    mw.addonManager.writeConfig(__name__, config) # write the config with changes
    print("ERROR localization: ", text)
    showText(text, type="error")


def get_loc(par1, default=""):
    """get data from localization = config["LOCALIZATION"][language_name] """
    try:
        ret = localization[par1]
        return ret
    except Exception as e:        
        print("ERROR get_loc(): ", e)
        return default  
    

def get_config():
    """receives the addon config"""
    return mw.addonManager.getConfig(__name__)


def write_config(cfg):
    """writes all changes to the addon config"""
    mw.addonManager.writeConfig(__name__, cfg)
    

def set_gs(key, val="", hint=""):
    """writes to 'GLOBAL_SETTINGS' and saves"""
    config["GLOBAL_SETTINGS"][key] = val
    if hint != "" :
        config["GLOBAL_SETTINGS"][key+" ?"] = hint
    mw.addonManager.writeConfig(__name__, config)    

def get_gs(key):
    try:
        ret = config["GLOBAL_SETTINGS"][key]
        return ret
    except Exception as e:        
        print("ERROR get_gs(): ", e)
        return None
    
def key_in_gs(key):
    return key in config["GLOBAL_SETTINGS"]    
# =============================================================================






