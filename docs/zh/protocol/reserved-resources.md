# 會被佔用的資源

| 資源 | 用途 |
| --- | --- |
| `UFRAME[8]`、`UTOOL[1]` | `MAPPDK_SERVER` 啟動時就設定，編號在 `mappdk_server.kl` 的 `CONST` |
| `R[81]` | 速度 |
| `R[82]` | 加速度 |
| `R[83]` | CNT |
| `PR[81]` | 目標位置 |

workcell 用到同編號會被蓋掉。程式裡用 `fanuc.RESERVED` 可以拿到這份清單。

---
*最後更新：2026-08-31*
