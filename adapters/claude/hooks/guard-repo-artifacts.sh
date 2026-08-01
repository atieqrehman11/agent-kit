#!/usr/bin/env bash
# PreToolUse guard (Write|Edit|MultiEdit) — shared by Echostar and Under Armour.
#
# Rule: generated design artifacts — Word docs, diagrams, decks, workbooks — must
# NOT be written into the real deployed code repositories; they belong in the local
# design workspace (echo-star-local/ for Echostar, ua-local/ for Under Armour).
# Editing actual code inside those repos is fine, so this only intercepts artifact
# file types and asks for confirmation (permissionDecision: "ask") — never hard-denies.
#
# Usage: guard-repo-artifacts.sh <protected-segment> [<protected-segment> ...]
#   e.g. guard-repo-artifacts.sh gitlab      (Echostar real repos live under gitlab/)
#        guard-repo-artifacts.sh github      (Under Armour real repos live under github/)
#
# Reads the hook payload on stdin. Emits an "ask" decision when a generated artifact
# is about to land under any protected segment; otherwise stays silent (exit 0 = allow).

segments=("$@")
[ ${#segments[@]} -eq 0 ] && segments=("gitlab")

f="$(jq -r '.tool_input.file_path // empty' 2>/dev/null)"
[ -z "$f" ] && exit 0

# Only artifact file types are guarded; code files pass straight through.
case "$f" in
  *.docx|*.drawio|*.pptx|*.xlsx) ;;
  *) exit 0 ;;
esac

for seg in "${segments[@]}"; do
  case "$f" in
    */"$seg"/*)
      jq -nc --arg f "$f" --arg seg "$seg" '{
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "ask",
          permissionDecisionReason: ("Writing a generated artifact into a " + $seg + "/ repo: " + $f + "\nRule: design docs/diagrams/decks belong in the local design workspace, not the code repos. Confirm only if you explicitly intend to commit this into the repo.")
        }
      }'
      exit 0
      ;;
  esac
done
exit 0
