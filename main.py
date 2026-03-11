import sys
import serial
import time
import json
import subprocess
from gpiozero import Button
sys.path.append('GM_RAG')
sys.path.append('camera-vlm')
from DM_RAG import DM_RAG
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


#['espeak', '-ven+f3', text, '--stdout'] Female voice
#['espeak', '-ven-rp', text, '--stdout'] English
#['espeak', '-ven-rp', text, '--stdout'] slow dows
def speak_text(text):
    # This takes the text, turns it into audio data (stdout), 
    # and "pipes" it directly into pw-play
    ps = subprocess.Popen(['espeak', '-ven-rp', '-s', '100', '--stdout', text], stdout=subprocess.PIPE)
    subprocess.run(['pw-play', '-q'], stdin=ps.stdout)
    ps.wait()

# Placeholder function for sheet detection logic
import random
def detect_sheet():
    # 1. If the function doesn't have a counter yet, create one
    if not hasattr(detect_sheet, "counter"):
        detect_sheet.counter = 0
        
    # 2. Add 1 to the counter every time the function is called
    detect_sheet.counter += 1
    
    # 3. Return True if we are at 4 or less, False if we hit 5
    if detect_sheet.counter <= 4:
        print(f"[Camera Simulation] Sheet {detect_sheet.counter} detected! ✓")
        return True
    else:
        print("[Camera Simulation] No more sheets detected. ✗")
        return False

# This is a simulated version of the DM's first turn, which will return the scripted responses and types in sequence.
def first_turn(party_dsc):
    # The opening story and a request for a die roll (Type 1)
    initial_story = "Welcome to the dark crypt. As you step inside, a skeleton drops from the ceiling! Roll a D20 for initiative to see who acts first."
    run_type = 1 
    
    return initial_story, run_type

# This is a simulated version of the DM's subsequent turns, which will return the scripted responses and types in sequence.
def next_turn(previous_llm_response, player_response, game_round):
    if not hasattr(next_turn, "step"):
        next_turn.step = 0
        
        # The 6-part simulated DM script that follows the first turn
        next_turn.responses = [
            "You rolled high and won initiative! What do you want to do?", 
            "You swing your weapon. It hits! The skeleton stumbles back. Do you press the attack or hold your ground?", 
            "You press the attack! Roll a D20 for damage.", 
            "The skeleton shatters into pieces! Suddenly, a hidden trapdoor opens under your feet. Roll a D20 for a dexterity saving throw.", 
            "You grab the ledge and pull yourself up. You notice a glowing chest in the corner. Do you open it?",
            "You open the chest and find the ancient relic. The adventure is complete. You win!"
        ]
        
        # The sequence for the loop: Mic, Mic, Die, Die, Mic, End
        next_turn.types = [0, 0, 1, 1, 0, -1]
        
    if next_turn.step >= len(next_turn.responses):
        return "The adventure has already ended.", -1
        
    current_response = next_turn.responses[next_turn.step]
    current_type = next_turn.types[next_turn.step]
    
    next_turn.step += 1
    
    return current_response, current_type

def runDie():
        print("[Die Simulation] Waiting for die roll...")
        roll = random.randint(1, 6)
        return roll

def get_transcript(ser, btn):
        print("[Mic Simulation] 'Listening' to player... ")
        return ""

def main():

    die = DieDetection()
    text = TextDetection()
    filename = "player-data/character_sheet.json"

    # game_master = DM_RAG("test")
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
    # btn.wait_for_press()  # This pauses the code until you physically push the button
    speak_text("Thank you. Let's begin the character registration.")
    
    player_count = 0

    while True:
        speak_text(f"Player {player_count+1} place your sheet under the camera")
        isMorePlayers = text.DetectMarkers()
        print(isMorePlayers)
        # Logic to detect sheet goes here
        if not isMorePlayers:
            break 
        
        player_count += 1

    print("Number of Players: ", player_count)

    # Read charcter json file and make into a string (party_dsc)
    try:
        with open(filename, 'r') as f:
            # Load the file as a Python dictionary
            data = json.load(f)
            
            # Convert it into a formatted string for the LLM
            # indent=2 makes it readable for debugging; omit it for a shorter string
            party_dsc = json.dumps(data, indent=2) 
            
        print("Party description prepared successfully.")
        print(party_dsc)  # Debugging: print the party description
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Using empty description.")
        party_dsc = "{}"

    game_round = 1
    # llm_response, type_of_run = game_master.first_turn(party_dsc)
    llm_response, type_of_run = first_turn(party_dsc)
    print(f"DM says: {llm_response} (Type {type_of_run})")
    speak_text(llm_response)

    while True:
        player_response = ""

        if type_of_run == -1: #END OF GAME
            end_game_message = "GAME OVER"

            speak_text(end_game_message)
            text.DeletePlayerJSON()
            break

        if type_of_run == 0: #MIC Type of run
            if btn.is_pressed:
                # This blocks until the user stops talking and text is ready
                player_response = engine.get_transcript(ser, btn)
                # player_response = get_transcript(ser, btn) TESTING
                print(f"User said: {player_response}")
                #DEBUGGING
                speak_text(player_response)            
            else:
                # Idle: Clear garbage data so the buffer is empty when you start talking
                if ser.in_waiting > 0:
                    ser.read(ser.in_waiting)
                time.sleep(0.01)

        if type_of_run == 1: #DIE Type of run
            player_response = die.runDie()
            # player_response = runDie() TESTING
            print(f"Die number Detected: {player_response}")

        game_round += 1
        #llm_response, type_of_run = game_master.next_turn(llm_response, player_response, game_round)
        llm_response, type_of_run = next_turn(llm_response, player_response, game_round)
        print(f"DM says: {llm_response} (Type {type_of_run})")
        speak_text(llm_response)

if __name__ == "__main__":
    main()