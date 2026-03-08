import sys
import serial
import time
import json
import subprocess
from gpiozero import Button
sys.path.append('GM_RAG')
sys.path.append('camera-vlm')
from DM_RAG import DM_RAG

from Die.src.DieDetection import DieDetection

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


#['espeak', '-ven+f3', text, '--stdout'] Female voice
#['espeak', '-ven-rp', text, '--stdout'] English
#['espeak', '-ven-rp', text, '--stdout'] slow dows
def speak_text(text):
    # This takes the text, turns it into audio data (stdout), 
    # and "pipes" it directly into pw-play
    ps = subprocess.Popen(['espeak', '-ven-rp', text, '--stdout'], stdout=subprocess.PIPE)
    subprocess.run(['pw-play', '-'], stdin=ps.stdout)
    ps.wait()

def main():

    die = DieDetection()
    filename = "character_sheet.json"

    game_master = DM_RAG("test")
    print("DB Loaded")

    # Setup Hardware
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
    btn = Button(BUTTON_PIN, pull_up=False)
    
    # Setup Speech Engine
    engine = SpeechEngine(WHISPER_EXEC, WHISPER_MODEL)

    print("--- Robot Ready ---")

    start_game_message = """Hello Welcome to Dungeons and 
    Dragons Game. I am your Dungeon Master. Everyone please
    fill in your character sheet. Press Button once ready"""

    speak_text(start_game_message)

    print("Waiting for players to finish sheets... Press physical button to continue.")
    btn.wait_for_press()  # This pauses the code until you physically push the button
    speak_text("Thank you. Let's begin the character registration.")
    
    player_count = 0

    while True:
        speak_text(f"Player {player_count+1} place your sheet under the camera")
    
        # Logic to detect sheet goes here
        # if not detect_sheet():
        #     break 
        
        player_count += 1

    print("Number of Players: ", player_count)

    # TODO: Read charcter json file and make into a string (party_dsc)
    try:
        with open(filename, 'r') as f:
            # Load the file as a Python dictionary
            data = json.load(f)
            
            # Convert it into a formatted string for the LLM
            # indent=2 makes it readable for debugging; omit it for a shorter string
            party_dsc = json.dumps(data, indent=2) 
            
        print("Party description prepared successfully.")
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using empty description.")
        party_dsc = "{}"

    game_round = 1
    #llm_response, type_of_run = game_master.first_turn(party_dsc)

    #speak_text(llm_response)

    while True:
        player_response = ""

        if type_of_run == -1: #END OF GAME
            speak_text(llm_response)

            end_game_message = "GAME OVER"

            speak_text(end_game_message)
            break

        if type_of_run == 0: #MIC Type of run
            if btn.is_pressed:
                # --- THE ONE FUNCTION CALL ---
                # This blocks until the user stops talking and text is ready
                player_response = engine.get_transcript(ser, btn)
                
                print(f"User said: {player_response}")
                #DEBUGGING
                #speak_text(player_response)            
            else:
                # Idle: Clear garbage data so the buffer is empty when you start talking
                if ser.in_waiting > 0:
                    ser.read(ser.in_waiting)
                time.sleep(0.01)

        if type_of_run == 1: #DIE Type of run
            player_response = die.runDie()
            print(f"Die number Detected: {player_response}")

        game_round += 1
        #llm_response, type_of_run = game_master.next_turn(llm_response, player_response, game_round)

if __name__ == "__main__":
    main()