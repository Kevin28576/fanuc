# 開始之前

ROBOGUIDE 虛擬控制器的一次性設定，設定存在 workcell 裡，之後每次開機
只要跑 MAPPDK，不用重設。

TP 選單用簡體標示，各版本用詞略有出入（例如 `装载` / `加载`）。
系統變數名稱永遠是英文，不會翻譯。

## 控制器上跑的是兩支 server

| 程式 | tag | port | 用途 |
| --- | --- | --- | --- |
| `MAPPDK_SERVER` | S8 | 18735 | 主連線，動作、I/O、位置查詢都走這條 |
| `MAPPDK_LOGGER` | S7 | 18736 | 第二條連線，只在需要邊移動邊查位置時才用得到 |

指令集一樣，差別只有 tag、port，跟 logger 不清 TP 畫面、不設
UFRAME/UTOOL。driver 是同步阻塞的，主連線送出移動指令後會卡到動作
結束，這段時間查不了位置。如果你的程式需要在移動過程中即時記錄
軌跡（`examples/trace_motion.py` 那種用法），才需要第二條連線；
單純讀寫位置、暫存器、I/O，S7 完全可以不設，跳過本文件所有提到 S7
的步驟即可。

## 確認控制器選項

要有這兩個：

- **R632**：KAREL
- **R648**：User Socket Messaging

查法：`菜单` → `下页` → `状态` → `版本识别` → 按 `ORDER FI`。

比較快的判斷方式：`一览` → `类型` 裡面有沒有 `KAREL程序` 這一項，
有就代表 R632 已經裝了。

兩個選項都沒裝的話，要在 ROBOGUIDE 對這台機器人做 Serialize / robot
options 更新，進 virtual robot edit wizard 把兩個選項加進去。這步
沒辦法繞過，選項沒裝，後面所有步驟都做不了。

確認完，繼續看[伺服器 tag 設定](server-tags.md)。

---
*最後更新：2026-08-31*
