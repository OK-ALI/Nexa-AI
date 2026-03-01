"""Quick import verification - one at a time with full error capture"""
import sys
import os

# Redirect to file to avoid encoding issues
log_file = open("import_results.txt", "w", encoding="utf-8")

tests = [
    ("config.settings", "Config"),
    ("core.kernel", "NexaKernel"),
    ("core.cognition.natural_responses", "NaturalResponses"),
    ("core.cognition.text_processing", "TextProcessor"),
    ("core.cognition.command_detection", "CommandDetector"),
    ("core.memory.memory_types", "ConversationMemory"),
    ("capabilities.system.system_control", "SystemControl"),
    ("capabilities.system.volume_controller", "VolumeController"),
    ("capabilities.system.wifi_controller", "WiFiController"),
    ("capabilities.system.brightness_controller", "BrightnessController"),
    ("capabilities.system.battery_manager", "BatteryManager"),
    ("capabilities.system.app_discovery", "AppDiscovery"),
    ("capabilities.system.window_manager", "WindowManager"),
    ("capabilities.system.file_manager", "FileManager"),
    ("capabilities.media.music_manager", "MusicManager"),
    ("capabilities.creative.game_manager", "GameManager"),
    ("capabilities.web.weather_service", "WeatherService"),
    ("capabilities.web.web_scraper", "WebScraper"),
]

errors = []
for module_name, class_name in tests:
    try:
        mod = __import__(module_name, fromlist=[class_name])
        cls = getattr(mod, class_name)
        msg = f"  OK {module_name}.{class_name}"
        print(msg)
        log_file.write(msg + "\n")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        msg = f"  FAIL {module_name}.{class_name}\n{tb}"
        print(msg)
        log_file.write(msg + "\n")
        errors.append(module_name)

summary = f"\nTotal: {len(tests)}, Passed: {len(tests)-len(errors)}, Failed: {len(errors)}"
print(summary)
log_file.write(summary + "\n")

if errors:
    log_file.write(f"Failed modules: {errors}\n")

log_file.close()
sys.exit(len(errors))
