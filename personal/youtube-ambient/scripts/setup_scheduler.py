"""Set up Windows Task Scheduler to run the pipeline once per day.

Run this script once:
    python scripts/setup_scheduler.py

It creates a task called "YT Ambient Daily Upload" that fires at 8:00 AM every day.
The task runs as the current user (interactive session — no password prompt needed).

To verify:
    schtasks /query /tn "YT Ambient Daily Upload"

To remove:
    schtasks /delete /tn "YT Ambient Daily Upload" /f
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TASK_NAME = "YT Ambient Daily Upload"
FIRE_TIME = "08:00"

PROJECT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
SCRIPT = PROJECT / "scripts" / "run_pipeline.py"
LOG_DIR = PROJECT / "logs"
LOG_FILE = LOG_DIR / "scheduler.log"

FFMPEG_DIR = (
    r"C:\Users\Muham.000\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1.1-full_build\bin"
)


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    ps = f"""
$action   = New-ScheduledTaskAction -Execute '{PYTHON}' -Argument '"{SCRIPT}" --auto' -WorkingDirectory '{PROJECT}'
$trigger  = New-ScheduledTaskTrigger -Daily -At "{FIRE_TIME}"
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 10) -StartWhenAvailable -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName "{TASK_NAME}" -Action $action -Trigger $trigger -Settings $settings -Force
Write-Output "Task registered: {TASK_NAME}"
Write-Output "Fires daily at {FIRE_TIME}."
"""

    result = subprocess.run(
        ["pwsh", "-NonInteractive", "-Command", ps],
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        # Try legacy powershell.exe as fallback
        result2 = subprocess.run(
            ["powershell", "-NonInteractive", "-Command", ps],
            capture_output=True,
            text=True,
        )
        if result2.stdout:
            print(result2.stdout)
        if result2.returncode != 0:
            print("ERROR:", result.stderr or result2.stderr)
            sys.exit(1)

    print(f"\nScheduler active. To verify:")
    print(f'  schtasks /query /tn "{TASK_NAME}"')
    print(f"\nTo remove:")
    print(f'  schtasks /delete /tn "{TASK_NAME}" /f')


if __name__ == "__main__":
    main()
