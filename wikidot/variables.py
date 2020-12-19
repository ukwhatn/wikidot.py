# -*- coding: utf-8 -*-

"""wikidot.variables

Global variables for wikidot.py

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

# login_data
logged_in = False  # type: bool
username = ""      # type: str
sessionid = ""     # type: str

# request_header
request_header = {
    "Cookie": "wikidot_token7=123456;",
    "Content-Type": ("application/x-www-form-urlencoded;charset=UTF-8")
}  # type: dict
