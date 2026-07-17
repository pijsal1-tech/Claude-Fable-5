# Double Review Checklist

## Review A — Logic & Correctness
- Does the change solve the real problem?
- Is the logic correct for all expected inputs?
- Are edge cases handled?
- Is there any contradiction with the project vision?
- Did I change behavior unintentionally?

## Review B — Architecture & Quality
- Is the change minimal and clean?
- Is the code readable and maintainable?
- Is the logic duplicated anywhere?
- Is this aligned with existing patterns?
- Is this safe to merge?

## Final Gate
Only approve the change if:
- Review A passes
- Review B passes
- No critical risk remains
- The result matches the project vision
