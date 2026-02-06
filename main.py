import sys
import serial
import time
from gpiozero import Button

# 1. Import your local module
sys.path.append('speech-to-text')
from speech_handler import SpeechEngine

# 2. Configuration
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 921600
BUTTON_PIN = 17

# Paths to Whisper (relative to main.py)
WHISPER_EXEC = "./speech-to-text/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = "./speech-to-text/whisper.cpp/models/ggml-tiny.bin"

def main():
    # Setup Hardware
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    btn = Button(BUTTON_PIN)
    
    # Setup Speech Engine
    engine = SpeechEngine(WHISPER_EXEC, WHISPER_MODEL)
    
    print("--- Robot Ready ---")

    while True:
        if btn.is_pressed:
            # --- THE ONE FUNCTION CALL ---
            # This blocks until the user stops talking and text is ready
            message = engine.get_transcript(ser, btn)
            
            print(f"User said: {message}")
            
            # TODO: Pass 'message' to Game Engine or Camera here
            
        else:
            # Idle: Clear garbage data so the buffer is empty when you start talking
            if ser.in_waiting > 0:
                ser.read(ser.in_waiting)
            time.sleep(0.01)

if __name__ == "__main__":
    main()