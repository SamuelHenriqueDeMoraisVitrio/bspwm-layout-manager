import subprocess
from datetime import datetime


def rofi_menu(options: list[str], prompt: str = "blm", message: str = "") -> str | None:
    """Opens a rofi dmenu and returns the selected option or None if cancelled."""
    if not options:
        rofi_error("No layouts saved yet.\nUse: blm save <name>")
        return None

    input_str = "\n".join(options)

    cmd = [
        "rofi", "-dmenu",
        "-p", prompt,
        "-i",                    # case insensitive
        "-no-custom",            # only allow listed options
        "-format", "s",          # return selected string
        "-theme-str", 'window {width: 500px;}',
    ]

    if message:
        cmd += ["-mesg", message]

    result = subprocess.run(cmd, input=input_str, capture_output=True, text=True)

    if result.returncode != 0:
        return None

    return result.stdout.strip()


def rofi_confirm(message: str) -> bool:
    """Opens a yes/no rofi prompt."""
    result = rofi_menu(["Yes", "No"], prompt=message)
    return result == "Yes"


def rofi_input(prompt: str) -> str | None:
    """Opens a rofi input box for free text."""
    result = subprocess.run(
        ["rofi", "-dmenu", "-p", prompt, "-theme-str", 'window {width: 400px;}'],
        input="",
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def rofi_error(message: str):
    """Shows an error message in rofi."""
    subprocess.run(["rofi", "-e", message])


def rofi_notify(message: str):
    """Shows a notification (uses notify-send if available, else rofi)."""
    result = subprocess.run(
        ["notify-send", "-a", "blm", "bspwm Layout Manager", message],
        capture_output=True
    )
    if result.returncode != 0:
        subprocess.run(["rofi", "-e", message])


def format_layout_list(layouts: dict) -> list[str]:
    """Formats layouts for display in rofi with metadata."""
    items = []
    for name, layout in layouts.items():
        saved_at = layout.get("saved_at", "")
        n_windows = len(layout.get("windows", []))

        # Format date
        try:
            dt = datetime.fromisoformat(saved_at)
            date_str = dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            date_str = ""

        label = f"{name}  ({n_windows} windows"
        if date_str:
            label += f" — {date_str}"
        label += ")"
        items.append(label)

    return items


def parse_selection(selection: str) -> str:
    """Extracts the layout name from a formatted rofi selection."""
    return selection.split("  (")[0].strip()
