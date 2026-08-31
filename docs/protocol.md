# MAPPDK protocol

*[中文版](zh/protocol.md)*

What strings Python sends the controller, checked against the KAREL
source in `driver/`. Split into the following, by topic:

| Document | Content |
| --- | --- |
| [Wire format](protocol/wire-format.md) | Sent/received string format, motion-command field widths, version detection |
| [Upstream commands](protocol/commands-upstream.md) | The command table compatible with the fanucpy upstream driver |
| [Extended commands](protocol/commands-extended.md) | Commands this project adds, per-command details, and real-hardware verification status |
| [Debugging notes](protocol/debugging-notes.md) | Debugging history from developing the extended commands (alarm history, getjpreg hanging) |
| [Error messages](protocol/errors.md) | Which exception class each driver error string maps to |
| [Driver limits](protocol/driver-limits.md) | Limits hardcoded in KAREL that can't be worked around (DIN is read-only, an out-of-range RDO aborts the server) |
| [Two connections](protocol/connections.md) | What S8 (main connection) and S7 (logger) each do |
| [Reserved resources](protocol/reserved-resources.md) | Registers and UFRAME/UTOOL numbers the driver uses |
| [Extending the driver](protocol/extending-the-driver.md) | Read this before adding a new command, or when weighing a deferred item |

For the controller-side environment setup (ROBOGUIDE, TP operation),
see [Controller setup](controller-setup.md).

> [!CAUTION]
> Everything below is a plain-text protocol over a plain TCP socket,
> with no authentication and no encryption at any layer. Never expose
> ports 18735/18736 to a network you don't fully trust; see the
> project README's security note.

---
*Last updated: 2026-08-31*
