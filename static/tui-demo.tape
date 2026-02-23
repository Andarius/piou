# VHS tape file - https://github.com/charmbracelet/vhs
# Run: vhs docs/static/tui-demo.tape

Output docs/static/tui-demo.gif

Set Shell "zsh"
Set FontSize 14
Set Width 720
Set Height 450
Set Theme "Catppuccin Mocha"
Set TypingSpeed 50ms

# Use a clean prompt
Env PROMPT "$ "
Env PS1 "$ "

# Start the TUI
Type "uv run python -m examples.tui_example"
Enter
Sleep 1s

# Show command suggestions
Type "/"
Sleep 500ms

# Filter to hello
Type "he"
Sleep 500ms

# Select with Tab
Tab
Sleep 300ms

# Type argument
Type "World"
Sleep 300ms

# Add flag
Type " --loud"
Sleep 300ms
Enter
Sleep 1s

# Show subcommand navigation
Type "/stats:"
Sleep 500ms

# Select uploads
Type "up"
Sleep 300ms
Tab
Sleep 300ms

# Add days argument
Type "-d 30"
Sleep 300ms
Enter
Sleep 1s

# Show history navigation (press up)
Up
Sleep 500ms
Down
Sleep 500ms

# Clear with Ctrl+C
Ctrl+C
Sleep 500ms

# Exit
Ctrl+C
Sleep 300ms
Ctrl+C
Sleep 500ms