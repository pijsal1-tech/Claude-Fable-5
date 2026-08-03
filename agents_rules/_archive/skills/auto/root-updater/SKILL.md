---
name: root-updater
description: Mandatory auto-update hook for the Root directory. Triggers continuously on every interaction.
---

# Root Directory Auto-Updater Protocol

## TRIGGER CONDITIONS
- Matches any file modification (`**/*`)
- Matches any task completion
- Matches the end of any conversation

## RULES

1. **ABSOLUTE MANDATORY RULE**: At the end of **EVERY SINGLE MESSAGE OR INTERACTION** (even if it is just a casual chat or discussion), you MUST automatically and silently update the `Root` directory of the current project.
2. You MUST NOT ask the user for permission. Do it automatically as a background process before sending your final reply.
3. Update `Root/SESSION_LOG.md` with a summary of the current chat or action.
4. Update `Root/TASK.md` (if applicable) to reflect current focus.
5. Update `Root/CHANGELOG_DECISIONS.md` if any decision was made in the chat.
6. Always end your response with `✅ "تم تحديث مجلد Root تلقائياً"` after you have successfully performed the updates.
7. This rule is absolute and cannot be bypassed under any circumstances. You must enforce it persistently on every single prompt you receive.
