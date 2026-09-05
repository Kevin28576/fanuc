# 開始之前

ROBOGUIDE 虛擬控制器的一次性設定，設定存在 workcell 裡，之後每次開機
只要跑 MAPPDK，不用重設。

TP 的選單語言跟著控制器本身的設定走。這份文件假設 TP 是繁體中文模式；
英文版（[Prerequisites](../../controller-setup/prerequisites.md)）
假設的是 TP 設成英文模式，兩邊選單名稱各自對照各自的語言。

TP 選單用詞各版本略有出入（例如 `裝載` / `加載`）。系統變數名稱不論
TP 設定哪種語言，永遠是英文。

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

- **KAREL**（常見編號 R632）
- **User Socket Messaging**（常見編號 R648）

選項編號不是每台控制器/每個軟體版本都一樣，實測過一台真機
（V9.30P/22），User Socket Messaging 顯示的編號是 **R636**，不是
R648。要對「名稱」，不要對「編號」：`菜單` → `下頁` → `狀態` →
`版本識別` → 按 `ORDER FI`，清單裡每個選項編號旁邊都有說明文字。

KAREL 這項比較快的判斷方式：`一覽` → `類型` 裡面有沒有
`KAREL程序` 這一項，有就代表 KAREL 已經裝了。User Socket Messaging
沒有這種捷徑，它不會單獨產生一個程式分類，只能靠 `ORDER FI` 清單
（或下面「`INTP-320 未定義的內置函數`」講的症狀）來判斷。

兩個選項都沒裝的話，要在 ROBOGUIDE 對這臺機器人做 Serialize / robot
options 更新，進 virtual robot edit wizard 把兩個選項加進去。這步
沒辦法繞過，選項沒裝，後面所有步驟都做不了。

## `PRIO-230 Ethernet Adapter error`

如果 `MAPPDK_SERVER`/`MAPPDK_LOGGER` 第一次要開 socket 時，`OPEN_COMM`
噴出這個警報，代表控制器的網路那端還沒準備好讓 R648 真的透過 Ethernet
通訊，不是這個專案 driver 的程式碼問題。依序檢查：

1. **確定真的裝了 User Socket Messaging**，不是只裝了 KAREL；
   這兩個選項很容易搞混，因為都跟這件事有關，但只有 User Socket
   Messaging 管的是這個警報講的 socket 層通訊。
2. **實機的話**（ROBOGUIDE 虛擬控制器不適用這條）：確認控制器的
   Ethernet 介面有實際接上，而且設好 IP（`菜單` → `設置` →
   `主機通信` → `TCP/IP`）。全新出廠、或從沒動過網路設定的機器人
   常常會踩到這個。
3. **port 沒有被佔用**，可能是別的 server tag，或上一次沒正常
   關閉留下的殘留連線；`輔助` → `中止程序`加上 `RESET`（見[執行
   driver](running.md)）通常就能清掉。

上游 fanucpy 也有人回報過這個警報
（[torayeff/fanucpy#35](https://github.com/torayeff/fanucpy/issues/35)），
跟「這是控制器端的前置條件、不是哪一邊的 KAREL 程式碼能修的」這個判斷
一致。

## `INTP-320 未定義的內置函數`

外觀跟「選項沒裝」一模一樣（KAREL、User Socket Messaging 都會先被
懷疑），但實測過一次，真正原因完全是另一回事：**`.pc` 用錯版本的
`ktrans` 編出來的。**

編譯出來的 `.pc` bytecode 跟 `ktrans` 當時鎖定的系統軟體版本是綁在
一起的；拿去載到跑不同版本的控制器上，一個完全正常的內建函式（這個
專案實際踩到的是 `MSG_DISCO`，在
[`driver/mappdk_comm.kl`](../../../driver/mappdk_comm.kl) 裡呼叫）
就會被判定成「未定義」，即使該裝的選項真的都有裝。警報會指出精確
的行號（`INTP-320 (MAPPDK_SERVER, 51) ...`），這正是它看起來像程式
碼真的有問題的原因，回頭去對 `.kl` 原始碼那一行，其實是完全正常、
寫法沒有問題的內建函式呼叫。

先確認控制器實際的系統軟體版本（`菜單` → `下頁` → `狀態` →
`版本識別`，看「Default Personality」那一行，例如 `V9.30P/22`
（不是下面 Boot Monitor 那一行，同一台控制器上兩者可能顯示不同版本
號）。然後用對應版本的 `ktrans /ver` 重新編譯（見
[driver/README.md](../../../driver/README.md#compiling-after-a-code-change)），
從 [`driver/upload/`](../../../driver/upload/) 底下對應版本的子
資料夾上傳，不要直接沿用上次編好的 `.pc`。

兩個選項都確認過了，而且要載的 `.pc` 跟這台控制器的實際版本對得上？
繼續看[伺服器 tag 設定](server-tags.md)。

---
*最後更新：2026-09-05*
