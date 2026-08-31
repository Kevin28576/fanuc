# 兩條連線

![Python 套件跟控制器之間的通訊協定](../../../media/CommProtocol.svg)

控制器上是兩支獨立的 KAREL 程式：

| 程式 | tag | port | 常數 |
| --- | --- | --- | --- |
| `MAPPDK_SERVER` | S8 | 18735 | `protocol.DEFAULT_PORT` |
| `MAPPDK_LOGGER` | S7 | 18736 | `protocol.LOGGER_PORT` |

把兩支原始碼對照著看，主迴圈完全一樣，都呼叫同一個 `HANDLE_CMD`，
[上游指令](commands-upstream.md)、[擴充指令](commands-extended.md)
兩邊都支援。差別只有三個：

- tag 和 port 不同
- logger 不執行 `TP_CLS`
- logger 不設 `UFRAME[8]` / `UTOOL[8]`，那是 server 在做的，兩支都設會打架

所以 logger 這個名字有點誤導，它不寫 log。用途是第二條連線：主連線
（S8）送 `movej` 之後會阻塞，這時可以從 logger（S7）查位置，軌跡記錄
（`MotionTracer`）就是這樣做的。只用單一連線的話，S7 可以不設，見
[控制器端設定](../controller-setup.md)。

---
*最後更新：2026-08-31*
