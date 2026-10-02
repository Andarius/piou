# VHS tape file - https://github.com/charmbracelet/vhs
# Run: vhs docs/static/tui-help.tape
# Showcases: Command help display when selecting commands

Output docs/static/tui-help.gif

Set Shell "zsh"
Set FontSize 14
Set Width 800
Set Height 540
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Use a clean prompt
Env PROMPT "$ "
Env PS1 "$ "

# Start the TUI (hidden from recording)
Hide
Type "uv run python -m examples.tui_example"
Enter
Sleep 1s
Show

# Show command suggestions - help appears for first command
Type "/"
Sleep 1.5s

# Navigate to hello - shows arguments and options
Down
Sleep 1.5s

# Navigate to add - shows two required arguments
Down
Sleep 1.5s

# Navigate to echo - shows options with defaults
Down
Sleep 1.5s

# Navigate to format - shows Literal type option
Down
Sleep 1.5s

# Clear and show stats command group - displays subcommands
Ctrl+C
Sleep 300ms
Type "/stats"
Sleep 1.5s

# Navigate into subcommands
Type ":"
Sleep 1s

# Show uploads subcommand help
Down
Sleep 1.5s

# Exit
Escape
Sleep 300ms