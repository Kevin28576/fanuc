# 設定 server tag

前置需求看過了嗎？見[開始之前](prerequisites.md)。

## S8（主連線，一定要設）

`菜單` → `設置` → `主機通信` → `顯示` → `服務器` → 選 `S8`：

| 項目 | 值 |
| --- | --- |
| 協議 | `SM` |
| 服務器IP | `127.0.0.1` |
| 端口 | `18735` |
| 啟動狀態 | `開始` |
| 當前狀態 | `已開始` |

`當前狀態` 不能直接改，按 `動作` → `定義`，再 `動作` → `啟動`。

## S7（第二條連線，只有需要邊移動邊查位置時才要設）

跟 S8 一樣的步驟，選 `S7`，端口填 `18736`。

不需要 S7 的話（大部分情境都不需要），這一段可以整段跳過，直接看
[載入 driver](loading-the-driver.md)。

## 兩邊都不用改 `$HOSTS_CFG`

driver 在建立連線時會自己用 `SET_VAR` 寫 `$SERVER_PORT`，要手動設的
只有 tag 編號、協議 `SM`、狀態 `已開始`，`$HOSTS_CFG` 不用碰。

## tag 編號要跟 driver 原始碼一致

`driver/mappdk_server.kl` 跟 `driver/mappdk_logger.kl` 裡的 `CONST`
區塊各寫死一個 `SERVER_TAG_NUM`（server 是 8，logger 是 7）。TP 上
設定的 tag 編號要跟這個數字一致，不然開不了 socket。**port 設對了
不代表 tag 也對**，兩個都要查，這是最容易漏掉的地方。

要用別的 tag 編號，得去改 `.kl` 原始碼裡的常數重新編譯，見
[driver/README.md](../../../driver/README.md)。

## 改用非預設的 port

18735/18736 只是預設值，協定本身沒有規定一定要用這兩個號碼。換掉
這兩個常見號碼不會多一層認證（見專案 README 的安全性提醒），但至少
能讓單純掃預設 port 的方式找不到控制器。

三個地方要用同一個號碼，任何一邊不一致，socket 就開不起來：

1. **KAREL 原始碼**：改 `mappdk_server.kl`/`mappdk_logger.kl` 裡
   `CONST` 區塊的 `PORT_NUMBER`（就在 `SERVER_TAG_NUM` 旁邊），重新
   編譯，把新的 `.pc` 重新載入控制器，見
   [driver/README.md](../../../driver/README.md)。
2. **TP 的 server 設定**：就是上面 S8/S7 設定畫面裡的 `端口` 欄位，
   改成一樣的號碼。
3. **Python 端**：明確帶新的 port，程式裡用
   `FanucRobot(host=..., port=12345)`，`fanuc` CLI 每次帶
   `--port 12345`，或用 `fanuc connect set --port 12345` 存起來一次
   就好。

port 對不起來，症狀跟 tag 對不起來一樣：`WinError 10061`、port 沒
`LISTENING`，見[驗證](verifying.md)。

設定完，繼續看[載入 driver](loading-the-driver.md)。

---
*最後更新：2026-08-31*
