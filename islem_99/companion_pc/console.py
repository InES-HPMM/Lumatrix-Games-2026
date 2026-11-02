"""Console line input that an outside event (the Pico joystick) can also end.

Plain input() blocks until Enter. On Windows we read keys with msvcrt instead,
so a joystick press can start the microphone while the prompt is waiting.
Elsewhere (or with piped input) it falls back to input().
"""
import sys
import time

try:
    import msvcrt
except ImportError:
    msvcrt = None


def interactive():
    return msvcrt is not None and sys.stdin.isatty()


def read_line(prompt, wake=None):
    """Like input(), but returns None if wake() fires while the line is still empty."""
    if wake is None or not interactive():
        return input(prompt)
    sys.stdout.write(prompt)
    sys.stdout.flush()
    chars = []
    while True:
        while msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in "\r\n":
                sys.stdout.write("\n")
                return "".join(chars)
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\x1a" and not chars:
                raise EOFError
            if ch in "\x00\xe0":
                msvcrt.getwch()  # Arrow and function keys come as two codes; ignore them.
            elif ch == "\b":
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
            elif ch.isprintable():
                chars.append(ch)
                sys.stdout.write(ch)
        sys.stdout.flush()
        if wake() and not chars:  # A press while typing is ignored.
            sys.stdout.write("\n")
            return None
        time.sleep(0.02)


def enter_pressed():
    """True if Enter was pressed; consumes all waiting keys."""
    pressed = False
    while msvcrt and msvcrt.kbhit():
        pressed = msvcrt.getwch() in "\r\n" or pressed
    return pressed


def drain_keys():
    """Forget keys pressed during a voice turn so they cannot start the next one."""
    enter_pressed()
