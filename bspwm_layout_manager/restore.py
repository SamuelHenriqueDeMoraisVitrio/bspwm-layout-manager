import subprocess
import time
import json


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip()


def get_launcher(window_class: str, cwd: str, command: str, shell: str = "") -> list[str]:
    """
    Builds the launch command for a window based on its class.
    Users can extend this to support more terminal emulators.
    """
    cls = window_class.lower()
    sh = shell or "/bin/sh"

    TERMINALS = ["alacritty", "kitty", "foot", "urxvt", "xterm", "wezterm", "st"]

    # Check if it's a terminal
    is_terminal = any(t in cls for t in TERMINALS)

    if is_terminal:
        # Try to detect what was running inside the terminal
        # and re-launch it
        inner_cmd = extract_inner_command(command, cwd)

        if "alacritty" in cls:
            cmd = ["alacritty", "--working-directory", cwd]
            if inner_cmd:
                cmd += ["-e", sh, "-c", f"{inner_cmd}; exec {sh}"]
            else:
                cmd += ["-e", sh]
            return cmd

        if "kitty" in cls:
            cmd = ["kitty", "--directory", cwd]
            if inner_cmd:
                cmd += [sh, "-c", f"{inner_cmd}; exec {sh}"]
            else:
                cmd += [sh]
            return cmd

        if "foot" in cls:
            cmd = ["foot", f"--working-directory={cwd}"]
            if inner_cmd:
                cmd += [sh, "-c", f"{inner_cmd}; exec {sh}"]
            else:
                cmd += [sh]
            return cmd

        # Generic fallback
        return [cls, "--working-directory", cwd]

    # Browsers
    BROWSERS = {
        "google-chrome": ["google-chrome-stable"],
        "chromium": ["chromium"],
        "firefox": ["firefox"],
        "brave": ["brave"],
    }
    for key, launcher in BROWSERS.items():
        if key in cls:
            return launcher

    # Generic fallback — try to use the class name as command
    return [window_class.lower().replace(" ", "-")]


def extract_inner_command(command: str, cwd: str) -> str:
    """
    Tries to extract the meaningful command running inside a terminal.
    Strips shell wrappers like bash/zsh/fish.
    """
    SHELLS = ["bash", "zsh", "fish", "sh", "nu"]
    parts = command.split()

    if not parts:
        return ""

    # If the main process is just a shell, nothing interesting to restore
    binary = parts[0].split("/")[-1]
    if binary in SHELLS:
        return ""

    # Skip terminal binary itself
    TERMINALS = ["alacritty", "kitty", "foot", "urxvt", "xterm", "wezterm", "st"]
    if binary in TERMINALS:
        return ""

    return command


def restore_layout(layout: dict, delay: float = 0.6):
    """
    Restores a saved layout by launching apps and organizing them
    using bspwm preselection.
    """
    windows = layout.get("windows", [])
    splits = layout.get("splits")
    desktop = layout.get("desktop", 1)

    # Switch to target desktop
    run(["bspc", "desktop", "-f", str(desktop)])
    time.sleep(0.3)

    if not windows:
        print("No windows to restore.")
        return

    # Launch windows in order using split preselections
    launch_from_tree(splits, windows, is_first=True, delay=delay)


def launch_from_tree(node: dict | None, windows: list, is_first: bool, delay: float):
    """
    Recursively walks the split tree and launches windows in the correct order,
    using bspc preselection to control placement.
    """
    if node is None:
        return

    if node["type"] == "window":
        # Find the matching window info
        win = find_window(node, windows)
        if win is None:
            return

        launcher = get_launcher(win["class"], win["cwd"], win["command"], win.get("shell", ""))
        subprocess.Popen(launcher)
        time.sleep(delay)
        return

    # It's a split node
    ratio = node.get("ratio", 0.5)
    split_type = node.get("split_type", "vertical")
    direction = "east" if split_type == "vertical" else "south"

    # Launch first child
    launch_from_tree(node.get("first"), windows, is_first=True, delay=delay)

    # Preselect for second child
    run(["bspc", "node", "-p", direction])
    run(["bspc", "node", "-o", str(ratio)])

    # Launch second child
    launch_from_tree(node.get("second"), windows, is_first=False, delay=delay)


def find_window(node: dict, windows: list) -> dict | None:
    """Matches a tree node to a saved window by node_id or class."""
    node_id = node.get("node_id")
    node_class = node.get("class", "").lower()

    # Try exact node_id match first
    for w in windows:
        if w["node_id"] == node_id:
            return w

    # Fallback: match by class
    for w in windows:
        if w["class"].lower() == node_class:
            return w

    return None
