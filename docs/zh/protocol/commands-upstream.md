# 上游指令

取自 `mappdk_cmd.kl` 的 `HANDLE_CMD`，跟原本 fanucpy 上游 driver 相容，
沒載入本專案的擴充 driver 也能用。

| 指令 | 參數 | 回應 | 方法 |
| --- | --- | --- | --- |
| `curpos` | 無 | `x=..,y=..,z=..,w=..,p=..,r=..` | `get_curpos()` |
| `curjpos` | 無 | `j=..,j=..`（沒有的軸是 `j=none`）| `get_curjpos()` |
| `ins_pwr` | 無 | kW | `get_ins_power()` |
| `movej` | 見[傳輸格式](wire-format.md#動作指令的欄位寬度) | `success` | `move("joint", ...)` |
| `movep` | 見[傳輸格式](wire-format.md#動作指令的欄位寬度) | `success` | `move("pose", ...)` |
| `mappdkcall` | `:<程式名>` | `success` | `call_prog()` |
| `getrdo` | `:<n>` | `0` / `1` | `get_rdo()` |
| `setrdo` | `:<n>:<true\|false>` | `success` | `set_rdo()` |
| `getdout` | `:<5 位補零>` | `0` / `1` | `get_dout()` |
| `setdout` | `:<5 位補零>:<true\|false>` | `success` | `set_dout()` |
| `setsysvar` | `:<變數名>:<T\|F>` | `success` | `set_sys_var()` |
| `exit` | 無 | `success`，然後斷線 | 用 `disconnect()` |

`setsysvar` 只吃布林（`T`/`F`），數值型系統變數要用擴充指令
`setsysvarnum`，見[擴充指令](commands-extended.md)。

---
*最後更新：2026-08-31*
