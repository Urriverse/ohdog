from pathlib import Path
import os, sys
import traceback


class Logger:
    def __init__(self):
        self.no_color = os.environ.get('NOCOLOR', '').lower() in ('1', 'true', 'yes', 'on')
        self.is_tty = sys.stderr.isatty()
        
    def _color(self, text: str, color: str) -> str:
        if self.no_color or not self.is_tty:
            return text
        colors = {
            'red': '\033[31m',
            'green': '\033[32m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'magenta': '\033[35m',
            'cyan': '\033[36m',
            'bold': '\033[1m',
            'reset': '\033[0m'
        }
        return f"{colors.get(color, '')}{text}{colors['reset']}"
    
    def error(self, *parts, file: str | os.PathLike | None = None, line: int | None = None, hint: str | None = None):
        prefix = self._color("error", "red") + ":"
        location = ""
        if file and line:
            file_str = self._color(str(file), 'cyan')
            line_str = self._color(str(line), 'magenta')
            location = f"\n  {self._color('-->', 'blue')} {file_str}:{line_str}"
        
        print(f"{prefix} {' '.join(str(i) for i in parts)}{location}", file=sys.stderr)
        
        if hint:
            print(f"  {self._color('=', 'blue')} {self._color('hint:', 'cyan')} {hint}", file=sys.stderr)
        
        sys.exit(1)
    
    def warning(self, *parts, file: str | os.PathLike | None = None, line: int | None = None):
        prefix = self._color("warning", "yellow") + ":"
        location = ""
        if file and line:
            file_str = self._color(str(file), 'cyan')
            line_str = self._color(str(line), 'magenta')
            location = f"\n  {self._color('-->', 'blue')} {file_str}:{line_str}"
        
        print(f"{prefix} {' '.join(str(i) for i in parts)}{location}", file=sys.stderr)
    
    def info(self, message: str):
        print(f"{self._color('   Fetching', 'green')} {message}", file=sys.stderr)
    
    def compiling(self, message: str):
        print(f"{self._color('   Compiling', 'green')} {message}", file=sys.stderr)
    
    def finished(self, message: str):
        print(f"{self._color('  Finished', 'green')} {message}", file=sys.stderr)
    
    def note(self, message: str):
        print(f"{self._color('  note:', 'cyan')} {message}", file=sys.stderr)


    def log_macro_error(self, e: Exception, macro_name: str, source_file: str | os.PathLike | None = None):
        tb = traceback.extract_tb(e.__traceback__)
        error_file = None
        error_line = None
        
        for frame in reversed(tb):
            if 'importlib' not in frame.filename and 'build.py' not in frame.filename:
                error_file = Path(frame.filename)
                error_line = frame.lineno
                break
        
        if not error_file:
            error_file = source_file
            error_line = 1
        
        self.error(
            f"macro '{macro_name}' failed: {str(e)}",
            file=error_file,
            line=error_line
        )


logger = Logger()
