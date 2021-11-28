#!/usr/bin/env python3
# Author: Antony Toron

from sintmint import *
import traceback

def main():
    print("Starting")

    #sintmint = SintMint()

    #target_entity = input("Please enter a name or entity: ")
    #sentiment_score, entity_category =
    #    sintmint.get_sentiment_score(target_entity)

def cleanup():
    pass

if __name__ == "__main__":
    try:
        main()
    except:
        traceback.print_exc()
        cleanup()

