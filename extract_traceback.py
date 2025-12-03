import re

log_path = r"dist\Nexa AI\_internal\data\logs\nexa_debug.log"

try:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        
    # Find the last occurrence of "Traceback" or "CRITICAL"
    if "Traceback" in content:
        print("--- TRACEBACK FOUND ---")
        print(content.split("Traceback")[-1])
    elif "CRITICAL" in content:
        print("--- CRITICAL ERROR FOUND ---")
        # Print the last 20 lines ending with the critical error
        lines = content.splitlines()
        critical_idx = -1
        for i, line in enumerate(lines):
            if "CRITICAL" in line:
                critical_idx = i
        
        if critical_idx != -1:
            print("\n".join(lines[max(0, critical_idx-20):]))
    else:
        print("No traceback or critical error found.")
        print("Last 20 lines:")
        print("\n".join(content.splitlines()[-20:]))

except Exception as e:
    print(f"Error reading log: {e}")
