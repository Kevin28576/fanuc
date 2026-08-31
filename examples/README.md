# examples/

Runnable scripts, each demonstrating exactly one feature of the
`fanuc` package. No shared helper module between them; every script
is meant to be read top to bottom on its own.

Run any of them directly:

```
python examples/demo.py
```

Running one prints the actual command sent to the controller and the
result, so what you see is closer to real output than reading the
docs. See the table in the [project README](../README.md#quick-start)
for what each script covers.

These scripts are in English. The same content, in Traditional
Chinese, with matching filenames, is in
[examples/chinese/](chinese/README.md).

<!-- ## Experimental: AI control

A separate, less battle-tested group of examples that put an LLM in
the loop instead of just wrapping one `fanuc` feature. Each has its
own README with a **USE WITH CAUTION** warning; read it before
running anything here against real hardware. Not published yet.

| Folder | What it does |
| --- | --- |
| [ai_chat/](ai_chat/README.md) | Type in plain language, Claude calls `fanuc` methods as tools to move the robot; four safety modes (manual/auto/plan/bypass) |
| [ai_voice/](ai_voice/README.md) | Same engine as `ai_chat/`, with speech in/out instead of typing |
| [ai_vision/](ai_vision/README.md) | Planned, not implemented yet |
-->


---
*Last updated: 2026-08-31*
