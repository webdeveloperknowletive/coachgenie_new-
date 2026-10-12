# Surgical Edits & Context Grounding Rules

## Purpose
Prevent unwanted full-file rewrites, code loss, and hallucinated modifications.

## Rules
1. **Targeted Diffs Only**: When editing files, modify only the exact block, function, or line necessary. Do not overwrite or regenerate entire files.
2. **Preserve Context & Logic**: Maintain existing comments, docstrings, imports, error handling, and formatting in unmodified sections.
3. **Verify Schemas Before Writing**: Always read the target file and related models before producing code. Do not invent columns, fields, or APIs.
4. **Backward Compatibility**: Preserve existing function signatures, endpoint contracts, and UI component props unless a refactor is explicitly requested.
