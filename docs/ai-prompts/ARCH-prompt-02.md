# AI Prompt: Architecture diagram revision

- Date: 15 Nov 2026
- Tool: Claude (same chat as ARCH-prompt-01)
- Purpose: Revise package diagram after team review

## Prompt

Review feedback on the package diagram: it looks highly coupled because three
"uses" arrows (Presentation, Application and Storage layers -> constants.py)
make every layer appear to depend on everything. In reality constants.py
imports nothing, so it is not coupling, only shared data.

Please:
1. Remove the three arrows to constants.py from the PlantUML diagram.
2. Put the note inside the constants.py box instead: "shared by all layers;
   imports nothing".
3. Keep the rest of the diagram unchanged (grayscale, top to bottom, same
   labels) and keep the layers aligned as much as possible.
4. Update the caption of Figure 1 in the wiki page to say that constants.py is
   shared by all layers and arrows to it are omitted on purpose.
5. Return the new PlantUML source, the new PNG, and only the changed part of
   the wiki page.