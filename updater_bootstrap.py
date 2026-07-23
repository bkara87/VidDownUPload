import sys
import os
import time
import shutil
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="VidDownUPload Auto-Updater Bootstrap")
    parser.add_argument("--current", required=True, help="Path to current executable")
    parser.add_argument("--new", required=True, help="Path to downloaded new executable")
    parser.add_argument("--pid", required=True, type=int, help="PID of process to wait for exit")
    args = parser.parse_args()

    current_exe = args.current
    new_exe = args.new
    target_pid = args.pid

    print(f"Waiting for parent process (PID {target_pid}) to terminate...")
    # Wait until parent process terminates
    while True:
        try:
            # Check if PID is still running
            os.kill(target_pid, 0)
            time.sleep(0.5)
        except OSError:
            # Process terminated
            break

    time.sleep(1)  # Extra buffer to release file locks

    try:
        print(f"Replacing {current_exe} with {new_exe}...")
        shutil.copy2(new_exe, current_exe)
        print("Update applied successfully! Restarting application...")
        subprocess.Popen([current_exe])
    except Exception as e:
        print(f"Failed to apply update: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
