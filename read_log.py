import sys
try:
    with open(r"dist\Nexa AI\_internal\data\logs\nexa_info.log", "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        print(f"Total lines: {len(lines)}")
        print("--- LAST 50 LINES ---")
        for line in lines[-50:]:
            print(line.strip())
except Exception as e:
    print(f"Error reading log: {e}")
