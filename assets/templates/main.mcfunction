# Bolt entry point for {{NAME}}.
# This file lives in `function/` with the `.mcfunction` extension — mecha+bolt
# parses Bolt syntax (Python loops, f-strings, defs) inside .mcfunction when
# both plugins are loaded. .bolt files belong in `module/`, not here.

for i in range(3):
    say f"Hello from bolt iteration {i}"
