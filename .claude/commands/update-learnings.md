---
description: Capture session learnings and update docs and skills for this project
allowed-tools: Read, Edit, Write, Glob
---

Review this session for learnings about working in this codebase.

**Do steps 1-2 silently. Only start outputting at step 3.**

## Step 1 (silent): Reflect

Identify what was non-obvious, missing, or corrected that would help future sessions:
- Workflows, conventions, or gotchas not yet documented
- Feedback or corrections from the user on how to approach work
- Project state changes: features shipped, decisions made, bugs resolved

## Step 2 (silent): Route changes

Invoke the `/ojhunt` skill, then read `update-docs.md` in full before deciding where
each learning belongs. Do not route from memory — read the file.

## Step 3: Show proposed changes

For each learning, show the target file and a concise diff. Keep additions brief —
skill files are loaded into every prompt.

## Step 4: Apply with approval

Ask the user which changes to apply. Only edit the files they approve.

**Important:** Documentation updates (skill files, README, docs/) are the primary
output of this command — always propose at least one. Memory updates are optional
and secondary; never substitute memory for documentation.
