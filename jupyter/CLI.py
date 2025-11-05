import sys
import signal
import subprocess
import threading
import time
from server import jupyter_process

def signal_handler(sig, frame):
    """Process Ctrl+C signal to stop terminal and Jupyter process"""
    print("\nStopping terminal and Jupyter Lab server...")
    if jupyter_process:
        jupyter_process.terminate()
        try:
            jupyter_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            jupyter_process.kill()
    sys.exit(0)

def interactive_terminal():
    """Interactive terminal function to repeat user input"""
    print("Interactive terminal started. Input will be repeated. Press Ctrl+C to exit.")
    
    while True:
        try:
            user_input = input(">>> ")
            print(f"You said: {user_input}")
        except EOFError:
            print("\nDetected EOF, exiting terminal...")
            break
        except KeyboardInterrupt:
            continue

if __name__ == "__main__":
    from server import jupyter_port
    print("Waiting for Jupyter Lab server to start...")
    time.sleep(10)
    print(f"Jupyter Lab server is running on http://localhost:{jupyter_port}")

    signal.signal(signal.SIGINT, signal_handler)
    
    # Open interactive terminal in a new thread
    terminal_thread = threading.Thread(target=interactive_terminal)
    terminal_thread.daemon = True
    terminal_thread.start()
    
    # Wait for the terminal thread to finish (this should never happen)
    try:
        terminal_thread.join()
    except KeyboardInterrupt:
        pass
    
    # Stop Jupyter process if it's still running
    if jupyter_process:
        print("Stopping Jupyter Lab server...")
        jupyter_process.terminate()
        try:
            jupyter_process.wait(timeout=5)
        except:
            jupyter_process.kill()