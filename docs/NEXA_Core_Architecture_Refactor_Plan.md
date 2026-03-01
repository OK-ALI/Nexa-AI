# NEXA Core Architecture Refactor Plan

Version: Core Kernel Upgrade

------------------------------------------------------------------------

## 1. Objective

Restructure NEXA to prevent task conflicts, idle interference, GPU
overload, and cross-module spaghetti dependencies.

Goal: - Centralized task governance - Priority-based execution - GPU
resource scheduling - Clean module layering - Zero interruption between
critical tasks

------------------------------------------------------------------------

## 2. High-Level Architecture Layers

### Layer 1 -- Core Kernel (NEW)

Responsible for control, not execution.

Components: - kernel.py - event_bus.py - priority_manager.py -
resource_manager.py (GPU Scheduler) - task_queue.py

Kernel Responsibilities: - Receive all events - Assign priority -
Allocate resources - Dispatch execution - Monitor task lifecycle

All modules must communicate through the Kernel.

------------------------------------------------------------------------

### Layer 2 -- Cognitive Layer

Thinking and reasoning components.

Modules: - brain.py - llm_manager.py - context_manager.py -
dynamic_preprocessor.py - prompt_builder.py - conversation_history.py -
smart_memory/ - response_cache.py

Rules: - Cannot directly call system or media modules - Must request
execution via Kernel

------------------------------------------------------------------------

### Layer 3 -- Capability Layer

Execution tools only.

Examples: - youtube_service.py - music_manager.py - file_manager.py -
window_manager.py - system_control.py - wifi_controller.py -
volume_controller.py - brightness_controller.py - weather_service.py -
screen_reader.py - notification_reader.py - gpu_monitor.py -
speaker_verification.py - pdf_generator.py

Rules: - Execute only - No decision-making - No cross-module calls

------------------------------------------------------------------------

### Layer 4 -- Interface Layer

User interaction.

Modules: - listener.py - tts.py - live2d_engine.py - companion/ -
web_scraper.py - sharing_service.py

------------------------------------------------------------------------

## 3. Priority System Design

Define strict numeric priority levels.

VOICE_INPUT = 100\
USER_COMMAND = 90\
NOTIFICATION_ALERT = 80\
SCREEN_QUERY = 70\
MEDIA_PLAYBACK = 60\
BACKGROUND_SYNC = 40\
IDLE_SUGGESTION = 20

Execution Rules:

1.  Higher priority interrupts lower priority.
2.  Equal priority tasks queue FIFO.
3.  Idle suggestions never interrupt active tasks.
4.  Locked state disables IDLE_SUGGESTION entirely.

Example Fix (NVP Conflict):

If NVP playing video (60)\
Idle suggestion (20) triggers

Kernel must reject idle suggestion.

------------------------------------------------------------------------

## 4. Task Queue Logic

Each task object must contain:

-   name
-   priority
-   gpu_required (bool)
-   estimated_vram
-   interruptible (bool)

Kernel Workflow:

1.  Receive task
2.  Compare priority with active task
3.  Interrupt or queue
4.  Ask ResourceManager for GPU allocation
5.  Execute or delay

------------------------------------------------------------------------

## 5. GPU Scheduler (ResourceManager)

Purpose: Prevent VRAM overflow and freezing.

Maintain:

-   total_vram = 8GB
-   safe_threshold = 7.2GB
-   active_gpu_tasks list

Example VRAM Budget:

LLaMA 3.1B (quantized) = 3.5GB\
Whisper Base = 1GB\
PaddleOCR = 1.5GB\
Vision Model = 2GB\
NVP Playback = 0.5GB

Allocation Logic:

1.  Check available VRAM
2.  If enough → allow
3.  If insufficient:
    -   Try suspending lower priority GPU task
    -   Else queue task
    -   Never exceed safe threshold

Optional Optimization: Unload Whisper or OCR after inactivity timeout.

------------------------------------------------------------------------

## 6. Idle System Redesign

Idle should not run blindly.

Rules:

-   Disabled when NEXA locked
-   Disabled during media playback
-   Disabled when GPU usage \> 70%
-   Only trigger if no active tasks
-   Check window focus before suggesting

Idle Flow:

1.  Kernel confirms system idle
2.  Kernel confirms priority safe
3.  Optional light context scan
4.  Generate suggestion
5.  Release resources immediately

------------------------------------------------------------------------

## 7. Structural Communication Rule

Hard Rule:

No module calls another module directly.

All communication:

Module → Kernel → Target Module

This eliminates hidden dependencies.

------------------------------------------------------------------------

## 8. Immediate Refactor Plan

1.  Create core/kernel/ directory
2.  Implement minimal Kernel skeleton
3.  Move gpu_monitor.py → resource_manager.py
4.  Add priority_manager.py
5.  Route all task execution through Kernel
6.  Disable direct calls between modules
7.  Integrate Idle logic into Kernel control
8.  Add VRAM safety checks before every GPU task

------------------------------------------------------------------------

## 9. Final Outcome

After implementation:

-   No idle interruptions during NVP
-   No suggestions while locked
-   No GPU overload
-   Clean module separation
-   Scalable architecture
-   Structured multitasking

NEXA becomes stable, predictable, and extensible.

------------------------------------------------------------------------

End of Refactor Plan.
