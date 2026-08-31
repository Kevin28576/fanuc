# Setting up server tags

Already been through the prerequisites? See
[prerequisites](prerequisites.md).

## S8 (main connection, always required)

`菜单` → `设置` → `主机通信` → `显示` → `服务器` → select `S8`:

| Field | Value |
| --- | --- |
| 协议 | `SM` |
| 服务器IP | `127.0.0.1` |
| 端口 | `18735` |
| 启动状态 | `开始` |
| 当前状态 | `已开始` |

`当前状态` can't be edited directly; press `动作` → `定义`, then
`动作` → `启动`.

## S7 (second connection, only needed when querying position while moving)

Same steps as S8, select `S7`, port `18736`.

If you don't need S7 (most use cases don't), skip this whole section
and go straight to [loading the driver](loading-the-driver.md).

## `$HOSTS_CFG` doesn't need editing on either

The driver writes `$SERVER_PORT` itself with `SET_VAR` when the
connection is established; the only things to set by hand are the tag
number, the `SM` protocol, and the `已开始` status. Leave
`$HOSTS_CFG` alone.

## The tag number has to match the driver source

`driver/mappdk_server.kl` and `driver/mappdk_logger.kl` each hardcode
a `SERVER_TAG_NUM` in their `CONST` block (8 for the server, 7 for the
logger). The tag number configured on the TP has to match this number,
or the socket won't open. **Getting the port right doesn't mean the
tag is right too**, both need checking; this is the easiest thing to
miss.

To use a different tag number, edit the constant in the `.kl` source
and recompile, see
[driver/README.md](../../driver/README.md).

Done? Continue to [loading the driver](loading-the-driver.md).

---
*Last updated: 2026-08-31*
