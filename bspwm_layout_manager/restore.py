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


def _get_existing_rules(win_class: str) -> list[tuple[str, str]]:
    """
    Returns existing bspc rules that match win_class as (selector, properties) pairs.
    Used to preserve permanent rules before removing a class's rules.
    """
    output = run(["bspc", "rule", "-l"])
    matches = []
    for line in output.splitlines():
        parts = line.split(" => ", 1)
        if len(parts) != 2:
            continue
        selector = parts[0].strip()
        properties = parts[1].strip()
        # selector format: Class:instance:name — match by class prefix
        selector_class = selector.split(":")[0]
        if selector_class.lower() == win_class.lower():
            matches.append((selector, properties))
    return matches


def _apply_desktop_rule(win_class: str, desktop: int) -> list[tuple[str, str]]:
    """
    Applies a temporary bspc rule to force a window to the target desktop.
    Returns existing rules for win_class so they can be restored afterward.
    """
    if not win_class:
        return []
    existing = _get_existing_rules(win_class)
    run(["bspc", "rule", "-a", win_class, f"desktop={desktop}"])
    return existing


def _remove_desktop_rule(win_class: str, saved_rules: list[tuple[str, str]]):
    """
    Removes the temporary bspc rule for the given class,
    then reapplies any permanent rules that existed before.
    """
    if not win_class:
        return
    run(["bspc", "rule", "-r", win_class])
    for selector, properties in saved_rules:
        # only restore permanent rules (desktop=^N) — skip blm's temporary ones
        if "desktop=^" in properties or "desktop=" not in properties:
            run(["bspc", "rule", "-a", selector] + properties.split())


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
    else:
        # Launch windows in order using split preselections
        launch_from_tree(splits, windows, is_first=True, delay=delay, desktop=desktop)

    # Restore floating windows after tiled ones
    restore_floating_windows(layout, delay)


def launch_from_tree(node: dict | None, windows: list, is_first: bool, delay: float, desktop: int):
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
        win_class = win.get("class", "")

        saved_rules = _apply_desktop_rule(win_class, desktop)
        subprocess.Popen(launcher)
        time.sleep(delay)
        _remove_desktop_rule(win_class, saved_rules)
        return

    # It's a split node
    ratio = node.get("ratio", 0.5)
    split_type = node.get("split_type", "vertical")
    direction = "east" if split_type == "vertical" else "south"

    # Launch first child
    launch_from_tree(node.get("first"), windows, is_first=True, delay=delay, desktop=desktop)

    # Preselect for second child
    run(["bspc", "node", "-p", direction])
    run(["bspc", "node", "-o", str(ratio)])

    # Launch second child
    launch_from_tree(node.get("second"), windows, is_first=False, delay=delay, desktop=desktop)


def restore_floating_windows(layout: dict, delay: float):
    """Launches floating windows and restores their position and size."""
    floating_windows = layout.get("floating_windows", [])
    desktop = layout.get("desktop", 1)

    for win in floating_windows:
        launcher = get_launcher(win["class"], win["cwd"], win["command"], win.get("shell", ""))
        win_class = win.get("class", "")
        rect = win.get("floatingRectangle", {})
        x = rect.get("x", 0)
        y = rect.get("y", 0)
        w = rect.get("width", 800)
        h = rect.get("height", 600)

        saved_rules = _apply_desktop_rule(win_class, desktop)
        subprocess.Popen(launcher)
        time.sleep(delay)
        _remove_desktop_rule(win_class, saved_rules)

        run(["bspc", "node", "-t", "floating"])

        # Read actual position/size after the window opened, then apply deltas
        node_json = run(["bspc", "query", "-T", "-n", "focused"])
        try:
            node_data = json.loads(node_json)
            rect_now = node_data["client"]["floatingRectangle"]
            dx = x - rect_now["x"]
            dy = y - rect_now["y"]
            dw = w - rect_now["width"]
            dh = h - rect_now["height"]
        except (KeyError, ValueError, TypeError):
            dx, dy, dw, dh = x, y, w, h

        run(["bspc", "node", "-v", str(dx), str(dy)])
        run(["bspc", "node", "--resize", "bottom-right", str(dw), str(dh)])


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
