# 錯誤訊息

driver 回應碼 `1` 時，訊息內容對應到 Python 這邊的例外類別。

| 訊息 | 例外 | 意思 |
| --- | --- | --- |
| `position-is-not-reachable` | `UnreachableError` | 超出範圍或姿態無解 |
| `R[81]-was-not-set` 等 | `MotionSetupError` | 動作參數暫存器寫不進去 |
| `PR[81]-was-not-set` | `MotionSetupError` | 位置暫存器寫不進去 |
| `wrong-command` | `UnsupportedCommandError` | driver 不認得 |
| `cannot-convert-joint-vals` | `CommandError` | 關節值轉換失敗 |
| `cannot-get-ins_pwr` | `CommandError` | 讀不到功率 |
| `cannot-get-reg` `cannot-set-reg` | `CommandError` | 暫存器存取失敗 |
| `cannot-get-preg` `cannot-set-preg` | `CommandError` | 位置暫存器存取失敗 |
| `cannot-get-sysvar` `cannot-set-sysvar` | `CommandError` | 變數不存在或型別不符 |
| `cannot-get-sreg` `cannot-set-sreg` | `CommandError` | 字串暫存器存取失敗 |
| `cannot-get-jpreg` `cannot-set-jpreg` | `CommandError` | 關節型位置暫存器存取失敗 |
| 其他 | `CommandError` | 其餘都歸這類 |

---
*最後更新：2026-08-31*
