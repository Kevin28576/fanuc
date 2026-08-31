# Running it

MAPPDK is a resident server, it has to keep running. Don't run it in
T2 mode. T2 requires holding SHIFT the entire time; letting go aborts
the program, and the TP shows `PROG-048 运行时放开了[Shift]键`.

## Startup steps

1. `辅助` → `中止程序`, clearing any leftover `已暂停` state
2. `RESET` to clear any fault
3. Switch mode to **AUTO**, TP switch to **OFF**
4. `一览` → select `MAPPDK` → press the green **CYCLE START** button on the panel

`MAPPDK` is just two lines:

```
1: RUN MAPPDK_SERVER
2: RUN MAPPDK_LOGGER
```

Using only S8, delete line 2, and [server tag setup](server-tags.md)
doesn't need S7 either.

On a successful start, the TP shows `MAPPDK SERVER started.` and the
status changes to `执行中`.

## Auto-start on boot? Tried it, gave up

Considered making MAPPDK start automatically on boot, so CYCLE START
wouldn't be needed every time. Tried two approaches, neither worked:

- **Background task** (the `菜单` → `背景执行` screen, slots 1-8): adding
  MAPPDK there gets `INTP-665 程序的背景执行不能`; this program can't
  run in background mode.
- **`设置` → `选择程序`** (`程序选择模式`/`自动运行开始方法`): dug
  through three levels; this whole page is actually about "which
  program an external PLC/UOP signal selects and starts", a different
  thing from "automatically run a specific program on boot", don't
  waste time looking here. Leave both settings at the default `其他`,
  don't change to `UOP` unless a PLC is actually connected.

Whether some other screen can do this hasn't been confirmed; that
would need the official FANUC manual or factory support to settle. For
now this stays a manual `CYCLE START`, stable and zero-risk, at the
cost of a few extra seconds after boot.

Started it? Continue to [verifying](verifying.md) that it actually
connects.

---
*Last updated: 2026-08-31*
