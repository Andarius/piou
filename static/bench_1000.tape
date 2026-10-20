# VHS tape file - https://github.com/charmbracelet/vhs
# Run: vhs docs/static/bench_1000.tape

Output docs/static/bench_1000.gif

Set Shell "zsh"
Set FontSize 13
Set Width 1000
Set Height 400
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Use a clean prompt
Env PROMPT "$ "
Env PS1 "$ "

# Start the TUI (hidden from recording)
Hide
Type "uv run python -m examples.http_bench_tui"
Enter
Sleep 1s
Show

# Run HTTP benchmark with 1000 requests
Type "/grid -n 1000 -b 3"
Enter
Sleep 20s
