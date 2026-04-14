---
description: Capture session learnings and update docs and skills for this project
allowed-tools: Read, Edit, Write, Glob
---

Review this session for learnings about working in this codebase.

## Step 1: Reflect

What was non-obvious, missing, or corrected that would help future sessions?
- Workflows, conventions, or gotchas not yet documented
- Feedback or corrections from the user on how to approach work
- Project state changes: features shipped, decisions made, bugs resolved

## Step 2: Route changes

Invoke the `/ojhunt` skill and read its `update-docs.md` sub-skill to decide where
each learning belongs in the project's documentation layers.

## Step 3: Show proposed changes

For each learning, show the target file and a concise diff. Keep additions brief —
skill files are loaded into every prompt.

## Step 4: Apply with approval

Ask the user which changes to apply. Only edit the files they approve.

**Important:** Documentation updates (skill files, README, docs/) are the primary
output of this command — always propose at least one. Memory updates are optional
and secondary; never substitute memory for documentation.
