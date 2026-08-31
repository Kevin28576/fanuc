# 擴充 driver

要幫 driver 加新指令、或評估要不要動 KAREL 原始碼時看這份。

## 加指令的步驟

1. `driver/mappdk_ext.kl` 加 ROUTINE
2. `driver/mappdk_cmd.kl` 的 `HANDLE_CMD` 加一段分派
3. 用到新的內建函式的話，`mappdk_server.kl` 和 `mappdk_logger.kl` 要加
   `%ENVIRONMENT`。環境檔在 WinOLPC 的 `Versions/V940-1/support`，
   grep 一下就知道某個函式在哪個 `.ev`
4. `cd driver` 再跑 ktrans，輸出的 `.pc` 會落在當前目錄，複製過去覆蓋
   `driver/upload/` 裡的舊檔，再從 TP 載入，步驟見
   [driver/README.md](../../../driver/README.md)
5. `protocol.py` 加 `encode_*` / `parse_*`，`robot.py` 加方法
6. `tests/test_protocol.py` 補格式測試，不需要實機

要先試指令可以用 `robot.send_raw()` 直接送字串，不用馬上包成方法。

## `%ENVIRONMENT` 的坑

有兩個。

一是只要宣告了任何一個，ktrans 就不再自動載入預設的延伸環境，
`$GROUP`、`CALL_PROGLIN`、`MSG_CONNECT` 這些會突然找不到，用到的必須
全部列出來。但 `CORE` 和 `SYSTEM` 是預設就載入的，再宣告一次會得到
`Cannot load environment file, program already exists`。

二是指示詞加環境的總數有上限。目前是 5 個指示詞（`%STACKSIZE`、
`%NOLOCKGROUP`、`%NOPAUSE`、`%ALPHABETIZE`、`%COMMENT`）配 7 個環境，
已經在邊緣。再加一個環境就會出現看起來毫不相干的
`Id must be defined before this use. Id: IO_RDO`。拿掉任何一個指示詞
或環境就會過，所以不是某個特定組合有問題。要再加環境的話，得先評估
哪個指示詞可以捨棄。

這個上限也是 RDO 存取範圍檢查放在 Python 而不是 KAREL 的原因，見
[driver 的限制](driver-limits.md#rdo-超界會讓整支-server-中止)。

## 還沒做的（暫緩）

**動作中斷、暫停、續行**：評估過，暫緩不做。跟讀寫暫存器這類
「查詢/資料」指令不一樣，這個需要跨任務控制正在執行動作的
`MAPPDK_SERVER`（KAREL 的 `PAUSE`/`ABORT <程式名>` 這類跨任務語法），
具體用法沒有查證過，而且一旦用錯，機器人可能停在中間狀態或觸發安全
機制，代價比讀寫暫存器出錯高很多，不適合用「先猜、編譯、卡住再
RESET」這套方法在實機上試。要重啟這項，需要先有查證過的 KAREL 跨
任務控制文件或範例，不是單靠現場試誤能穩妥解決的。

寫數值型系統變數、字串暫存器 `SR[n]`、關節型位置暫存器這三項已經寫在
`mappdk_ext.kl`（`setsysvarnum`/`getsreg`/`setsreg`/`getjpreg`/
`setjpreg`，見[擴充指令](commands-extended.md)），全部都已經在實機
驗證過。讀警報歷史試過，`ERR_DATA` 那個做法目前沒找到能用的方式，
已經退回只能讀最近一筆，見[疑難排解](debugging-notes.md#警報歷史讀不到)。

---
*最後更新：2026-08-31*
