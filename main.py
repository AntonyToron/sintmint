#!/usr/bin/env python3
# Author: Antony Toron

from sintmint import *

def main():
    print("Starting")

    sintmint = SintMint()
    sintmint.analyze_text("This is a pretty cool project")

def cleanup():
    pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Exiting due to error: " + e)
        cleanup()

