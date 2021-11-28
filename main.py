#!/usr/bin/env python3
# Author: Antony Toron

from sintmint import *
import traceback

def main():
    print("Starting")

    sintmint = SintMint()
    sintmint.get_sentiment_score("Nikola Tesla")

def cleanup():
    pass

if __name__ == "__main__":
    try:
        main()
    except:
        traceback.print_exc()
        cleanup()

