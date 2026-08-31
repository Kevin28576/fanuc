# 驗證

## port 有沒有真的開著

```
netstat -ano | findstr "18735 18736"
```

兩個都要看到 `LISTENING`（只用 S8 的話只會有 18735）。PID 對應虛擬
控制器的程序，可以在 `Robot_1\services.txt` 對照確認是不是同一個
workcell。

## Python 這邊連不連得上

```
fanuc status
```

看到 `driver: fanuc-driver 0.2.0` 就代表擴充 driver 生效了，不只是
連上上游版本。連線參數（`--host`/`--port` 等）不想每次都打，可以先
用 `fanuc connect set` 存起來，見 [README.zh.md](../../../README.zh.md) 的
指令列章節。

## 出問題時

| 症狀 | 原因 |
| --- | --- |
| `WinError 10061` | port 沒 LISTENING。ROBOGUIDE 沒開、MAPPDK 沒跑，或 tag 編號跟 driver 對不上，見[伺服器 tag 設定](server-tags.md) |
| `PROG-048 運行時放開了[Shift]鍵` | 在 T1/T2 模式跑，改 AUTO |
| `INTP-106 不能開始執行` | 程式停在 `已暫停` 而且有沒清的錯誤，先 `中止程序` 再 `RESET` |
| `MCTL-003 系統處於錯誤狀態` | 按 `RESET`，還在就檢查急停跟 fault |
| TP 顯示 started 但 port 沒開 | tag 編號跟 driver 原始碼裡的 `SERVER_TAG_NUM` 不符 |
| 18735 通、18736 不通 | S7 沒設或沒啟動，或 `MAPPDK` 程式裡第 2 行 `RUN MAPPDK_LOGGER` 被刪了 |
| `類型` 裡沒有 `KAREL程序` | R632 選項沒裝，見[開始之前](prerequisites.md) |
| `fanuc status` 顯示上游版本（不是 `fanuc-driver x.x.x`） | 載入的是舊版或上游 `.pc`，重新載入 `driver/upload/` 裡的檔案 |

程式卡住、Python 端一直沒回應：`輔助` → `中止程序`，再照
[執行](running.md)重跑一次 MAPPDK。

---
*最後更新：2026-08-31*
