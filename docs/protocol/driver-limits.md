# Driver limits

Hardcoded in KAREL; working around any of these means editing the
source and recompiling.

| Limit | Where | Impact |
| --- | --- | --- |
| Axis count is a single character | `mappdk_cmd.kl`, where `MOVEJ`/`MOVEP` parse the axis count | Motion commands top out at 9 axes |
| Server tag is a single character | `mappdk_comm.kl`, where `OPEN_COMM` builds the tag string | Only S1 through S9 |
| `setsysvar` only accepts T/F | `SET_SYS_VAR` in `mappdk_cmd.kl` | Numeric system variables need `setsysvarnum` (extended command) |
| Response is `STRING[254]` | `mappdk_server.kl`, the `resp` variable declaration | Upper bound on a single response's length |
| Single connection, synchronous and blocking | `mappdk_server.kl`, `OPEN_COMM`/main loop | A server can only serve one client at a time; a motion command blocks until it finishes. The second connection is the logger, see [two connections](connections.md) |
| `DIN[]` is read-only to user programs | KAREL language level | No way to write/simulate DI from a user KAREL program; ktrans rejects it at compile time regardless of the TP's SIM mode, this path has been abandoned, see below |

## DIN can't be written or simulated

Tried adding a `setdin` command that assigns directly to
`DIN[din_num]` on the KAREL side, the same approach as the already
working `SET_DOUT` (`mappdk_cmd.kl`, which writes `DOUT[]`), just with
DIN being an input array instead. `ktrans` rejected it outright at
compile time:

```
This system Id is "write protected" from KAREL user programs.  Id: DIN
```

This isn't "deferred after a risk assessment"; the KAREL language
itself simply doesn't allow it: `DIN[]` is read-only to user programs,
entirely independent of whether a point on the TP is set to simulation
(SIM) mode (it doesn't even compile, so it never gets that far). DI
simulation is only possible through the TP's own operator panel (if
the model/version supports it); this package's driver has fully
abandoned this path, don't try the same approach again.

## RDO out of range aborts the whole server

RDO numbers also used to be read as a single character; numbers 10 and
above got truncated to their first digit with no error. This project's
driver reads to the end of the string instead; connecting to the
upstream driver, the Python side applies the old limit itself.

**Accessing an RDO the controller doesn't have aborts the entire
MAPPDK_SERVER.** The TP shows:

```
PRIO-002 端口号不正确
```

Recovering needs RESET and rerunning MAPPDK. KAREL itself can't guard
against this: `GET_PORT_VAL` needs the `io_rdo` constant, and adding
the `IOSETUP` environment would push past ktrans's limit on the total
number of directives plus environments (see
[extending the driver](extending-the-driver.md#the-environment-pitfalls)).
So the limit lives in Python instead: `protocol.MAX_RDO_NUM` defaults
to 8, and can be raised by passing `max_rdo` when constructing
`FanucRobot`. DI and DO carry the same risk.

---
*Last updated: 2026-08-31*
