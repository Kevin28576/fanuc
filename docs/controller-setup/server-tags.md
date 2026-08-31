# Setting up server tags

Already been through the prerequisites? See
[prerequisites](prerequisites.md) (including the note there about
these English menu labels being unverified against a real screen).

## S8 (main connection, always required)

`MENU` → `SETUP` → `Host Comm` → `DETAIL` → `Servers` → select `S8`:

| Field | Value |
| --- | --- |
| Protocol | `SM` |
| Server IP | `127.0.0.1` |
| Port | `18735` |
| Start Status | `START` |
| Current Status | `STARTED` |

`Current Status` can't be edited directly; press `ACTION` → `DEFINE`,
then `ACTION` → `START`.

## S7 (second connection, only needed when querying position while moving)

Same steps as S8, select `S7`, port `18736`.

If you don't need S7 (most use cases don't), skip this whole section
and go straight to [loading the driver](loading-the-driver.md).

## `$HOSTS_CFG` doesn't need editing on either

The driver writes `$SERVER_PORT` itself with `SET_VAR` when the
connection is established; the only things to set by hand are the tag
number, the `SM` protocol, and the `STARTED` status. Leave
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

## Using a non-default port

18735/18736 are just the defaults; nothing in the protocol requires
them specifically. Moving off the well-known ports doesn't add
authentication (see the security note in the project README), but it
does mean a plain scan of the default ports won't immediately find the
controller.

Three places have to agree on the same number, or the socket simply
won't open:

1. **KAREL source**: edit `PORT_NUMBER` in the `CONST` block of
   `mappdk_server.kl`/`mappdk_logger.kl` (right next to
   `SERVER_TAG_NUM`), recompile, and reload the new `.pc` onto the
   controller. See [driver/README.md](../../driver/README.md).
2. **TP server config**: the `Port` field on this page's S8/S7 setup
   screen above, changed to match.
3. **Python side**: pass the new port explicitly, `FanucRobot(host=...,
   port=12345)` in code, `--port 12345` on every `fanuc` CLI call, or
   save it once with `fanuc connect set --port 12345`.

Mismatched port behaves exactly like a mismatched tag: `WinError
10061`, port not `LISTENING`, see [verifying](verifying.md).

Done? Continue to [loading the driver](loading-the-driver.md).

---
*Last updated: 2026-08-31*
