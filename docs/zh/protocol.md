# MAPPDK 協定

*[English](../protocol.md)*

Python 跟控制器之間送什麼字串，內容對照 `driver/` 的 KAREL 原始碼。
細節分成以下幾份，按主題分開看：

| 文件 | 內容 |
| --- | --- |
| [傳輸格式](protocol/wire-format.md) | 送出/收到的字串格式、動作指令欄位寬度、版本偵測 |
| [上游指令](protocol/commands-upstream.md) | 跟 fanucpy 上游 driver 相容的指令表 |
| [擴充指令](protocol/commands-extended.md) | 本專案加的指令、每個指令的細節與實機驗證狀態 |
| [疑難排解](protocol/debugging-notes.md) | 擴充指令開發過程中的除錯經過（警報歷史、getjpreg 卡住） |
| [錯誤訊息](protocol/errors.md) | driver 回應的錯誤字串對應到哪個例外類別 |
| [driver 的限制](protocol/driver-limits.md) | 寫死在 KAREL 裡、改不了的限制（DI 唯讀、RDO 超界會中止 server） |
| [兩條連線](protocol/connections.md) | S8（主連線）跟 S7（logger）分別做什麼 |
| [會被佔用的資源](protocol/reserved-resources.md) | driver 用掉的暫存器、UFRAME/UTOOL 編號 |
| [擴充 driver](protocol/extending-the-driver.md) | 要加新指令、或評估暫緩項目時看這份 |

控制器端的環境設定（ROBOGUIDE、TP 操作）見
[控制器端設定](controller-setup.md)。

---
*最後更新：2026-08-31*
