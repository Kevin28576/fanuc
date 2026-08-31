# 設定 server tag

前置需求看過了嗎？見[開始之前](prerequisites.md)。

## S8（主連線，一定要設）

`菜单` → `设置` → `主机通信` → `显示` → `服务器` → 選 `S8`：

| 項目 | 值 |
| --- | --- |
| 协议 | `SM` |
| 服务器IP | `127.0.0.1` |
| 端口 | `18735` |
| 启动状态 | `开始` |
| 当前状态 | `已开始` |

`当前状态` 不能直接改，按 `动作` → `定义`，再 `动作` → `启动`。

## S7（第二條連線，只有需要邊移動邊查位置時才要設）

跟 S8 一樣的步驟，選 `S7`，端口填 `18736`。

不需要 S7 的話（大部分情境都不需要），這一段可以整段跳過，直接看
[載入 driver](loading-the-driver.md)。

## 兩邊都不用改 `$HOSTS_CFG`

driver 在建立連線時會自己用 `SET_VAR` 寫 `$SERVER_PORT`，要手動設的
只有 tag 編號、协议 `SM`、狀態 `已开始`，`$HOSTS_CFG` 不用碰。

## tag 編號要跟 driver 原始碼一致

`driver/mappdk_server.kl` 跟 `driver/mappdk_logger.kl` 裡的 `CONST`
區塊各寫死一個 `SERVER_TAG_NUM`（server 是 8，logger 是 7）。TP 上
設定的 tag 編號要跟這個數字一致，不然開不了 socket。**port 設對了
不代表 tag 也對**，兩個都要查，這是最容易漏掉的地方。

要用別的 tag 編號，得去改 `.kl` 原始碼裡的常數重新編譯，見
[driver/README.md](../../../driver/README.md)。

設定完，繼續看[載入 driver](loading-the-driver.md)。

---
*最後更新：2026-08-31*
