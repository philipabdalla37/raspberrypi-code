import sys
import serial
import time
import json
import subprocess
import requests
from gpiozero import Button

sys.path.append('camera-vlm')
# from DM_RAG import DM_RAG
from GameSheet.src.TextDetection import TextDetection
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

# API endpoint for LLM
API = "https://9swj0rlwrm9wu1-8000.proxy.runpod.net/"

#['espeak', '-ven+f3', text, '--stdout'] Female voice
#['espeak', '-ven-rp', text, '--stdout'] English
#['espeak', '-ven-rp', text, '--stdout'] slow dows
def speak_text(text):
    # Add leading punctuation (commas/dots) to create a natural pause 
    #    that 'wakes up' the speakers before words are spoken.
    padded_text = f", , {text}"
    
    # -ven-rp is English (Received Pronunciation). 
    #    You can also use -ven+m3 for a male voice or -ven+f3 for female.
    #    -a 200 increases the volume to help trigger some auto-gain hardware.
    ps = subprocess.Popen(
        ['espeak-ng', '-ven-ca+f3', '-s', '135', '-a', '200', '--stdout', padded_text], 
        stdout=subprocess.PIPE
    )
    
    # 3. Using -D default can sometimes help 'aplay' lock onto the driver faster.
    subprocess.run(['aplay', '-q', '-D', 'default'], stdin=ps.stdout) 
    ps.wait()

def main():
    die = DieDetection()
    text = TextDetection()
    filename = "player-data/player_data.json"

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

    print("[DEBUG] Waiting for players to finish sheets... Press physical button to continue.")
    btn.wait_for_press()  # This pauses the code until you physically push the button
    speak_text("Thank you. Let's begin the character registration.")

    player_count = 0

    while True:
        player_count += 1
        speak_text(f"Player {player_count} place your sheet under the camera")
        isSheetDetected = text.DetectMarkers()  # Renamed for clarity; assumes True if sheet is present
        print(f"[DEBUG] Sheet detected for Player {player_count}: {isSheetDetected}")
        if not isSheetDetected:
            player_count -= 1  # Adjust back down since this player wasn't detected
            break

    print(f"[DEBUG] Number of Players: {player_count}")

    party_description = "{}"  # Initialize party_description variable
    # Read charcter json file and make into a string (party_description)
    try:
        with open(filename, 'r') as f:
        
            # Load the file as a Python dictionary
            data = json.load(f)
    
            # Convert it into a formatted string for the LLM
            # TODO: fix format of how json file is read to be compatible with LLM input. 
            # Currently the json file is read as a dictionary and then converted back to a string, which is not ideal.
            # party_description = json.dumps(data, indent=2)

        print("[DEBUG] Party description prepared successfully.")
    #  print(party_description)  # Debugging: print the party description
    except FileNotFoundError:
        print(f"[DEBUG] Warning: {filename} not found. Using empty description.")
        party_description = "{}"
    party_description = """
    {
    "Player1": {
        "player_name": "Miguel the Wizard",
        "strength": 18,
        "intelligence": 8,
        "charisma": 10,
        "dexterity": 14,
        "description": "A towering half-orc barbarian with a penchant for smashing doors and a surprisingly gentle heart."
    },
    "Player2": {
        "player_name": "Miguel the Wizard",
        "strength": 8,
        "intelligence": 19,
        "charisma": 12,
        "dexterity": 15,
        "description": "An elven wizard who spends more time reading ancient tomes than speaking to living beings. She carries a glowing crystal staff."
    },
    "Player3": {
        "player_name": "Miguel the Wizard",
        "strength": 10,
        "intelligence": 14,
        "charisma": 18,
        "dexterity": 16,
        "description": "A halfling bard with a silver tongue and a battered lute. Always ready to talk his way out of a fight or into a free drink."
    },
    "Player4": {
        "player_name": "Miguel the Wizard",
        "strength": 12,
        "intelligence": 11,
        "charisma": 14,
        "dexterity": 18,
        "description": "A human rogue who prefers the shadows. Quick with a dagger, quicker with a sarcastic quip, and deeply untrusting of authority."
    }
    }
"""
    #TODO: Remove varaible if we are not using it with LLM
    game_round = 1

    requests.post(
        API + "/init_game",
        json={"party_description": party_description}
    )

    response = requests.get(API + "/generate_turn")

    data = response.json()

    llm_response = data["event_json"]
    type_of_run = data["event_identifier"]

    print(f"[DEBUG] DM says: {llm_response} (Type {type_of_run})")
    speak_text(llm_response)

    while True:
        player_response = ""

        if type_of_run == -1:  # END OF GAME
            end_game_message = "GAME OVER. Thank you for playing."
            speak_text(end_game_message)
            text.DeletePlayerJSON()
            break

        elif type_of_run == 0:  # MIC Type of run
            while True:
                if btn.is_pressed:
                    # This blocks until the user stops talking and text is ready
                    player_response = engine.get_transcript(ser, btn)
                    print(f"User said: {player_response}")

                    #DEBUGGING
                    # speak_text(player_response)
                    break            
                else:
                    # Idle: Clear garbage data so the buffer is empty when you start talking
                    if ser.in_waiting > 0:
                        ser.read(ser.in_waiting)
                    time.sleep(0.01)

        elif type_of_run == 1:  # DIE Type of run
            player_response = die.RunDie()
            print(f"[DEBUG] Die number Detected: {player_response}")

        #TODO: What does this do?
        key = "player_input" if type_of_run == 0 else "dice_roll"
        response = requests.post(
            API + "/resolve_turn",
            json={
                "event_identifier": type_of_run,
                key: player_response
            }
        )
        result = response.json()
        #TODO: Remove varaible if we are not using it with LLM
        game_round += 1
        llm_response = result["outcome_json"]
        llm_response = json.dumps(llm_response)
        print(f"[DEBUG] DM says: {llm_response} (Type {type_of_run})")
        speak_text(llm_response)

        #TODO: What does this do?
        response = requests.get(API + "/generate_turn")
        data = response.json()
        llm_response = data["event_json"]
        type_of_run = data["event_identifier"]
        print(f"DM says: {llm_response} (Type {type_of_run})")
        speak_text(llm_response)



if __name__ == "__main__":
    main()