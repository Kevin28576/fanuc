# Reserved resources

| Resource | Used for |
| --- | --- |
| `UFRAME[8]`, `UTOOL[1]` | Set as soon as `MAPPDK_SERVER` starts; the numbers are in `mappdk_server.kl`'s `CONST` |
| `R[81]` | velocity |
| `R[82]` | acceleration |
| `R[83]` | CNT |
| `PR[81]` | target position |

Using the same numbers elsewhere in a workcell overwrites them.
`fanuc.RESERVED` gets you this list in code.

---
*Last updated: 2026-08-31*
