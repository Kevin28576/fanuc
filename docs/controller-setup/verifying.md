# Verifying

## Is the port actually open

```
netstat -ano | findstr "18735 18736"
```

Both should show `LISTENING` (only 18735 if you're only using S8). The
PID corresponds to the virtual controller's process, checkable against
`Robot_1\services.txt` to confirm it's the same workcell.

## Can Python actually connect

```
fanuc status
```

Seeing `driver: fanuc-driver 0.2.0` means the extended driver is
active, not just an upstream connection. If typing connection
parameters (`--host`/`--port` etc.) every time is annoying, save them
with `fanuc connect set` first, see the command-line section in
[README.md](../../README.md).

## When something's wrong

| Symptom | Cause |
| --- | --- |
| `WinError 10061` | port not LISTENING. ROBOGUIDE isn't open, MAPPDK isn't running, or the tag number doesn't match the driver, see [server tags](server-tags.md) |
| `PROG-048 运行时放开了[Shift]键` | running in T1/T2, switch to AUTO |
| `INTP-106 不能开始执行` | the program is stuck `已暂停` with an uncleared error; `中止程序` first, then `RESET` |
| `MCTL-003 系统处于错误状态` | press `RESET`; if it persists, check the e-stop and fault state |
| TP shows started but the port isn't open | the tag number doesn't match `SERVER_TAG_NUM` in the driver source |
| 18735 reachable, 18736 isn't | S7 wasn't configured or started, or line 2 (`RUN MAPPDK_LOGGER`) was deleted from `MAPPDK` |
| No `KAREL程序` under `类型` | the R632 option isn't installed, see [prerequisites](prerequisites.md) |
| `fanuc status` shows the upstream version (not `fanuc-driver x.x.x`) | an old or upstream `.pc` got loaded; reload the files from `driver/upload/` |

Something's stuck, or the Python side just isn't responding:
`辅助` → `中止程序`, then rerun MAPPDK following [running it](running.md).

---
*Last updated: 2026-08-31*
