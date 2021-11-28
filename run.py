#!/usr/bin/env python3
# Author: Antony Toron


def main():
    print("Starting")

def cleanup():
    pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Exiting due to error: " + e)
        cleanup()
