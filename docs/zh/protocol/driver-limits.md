# driver 的限制

寫死在 KAREL 裡，要突破就得改原始碼重新編譯。

| 限制 | 出處 | 影響 |
| --- | --- | --- |
| 軸數只取 1 個字元 | `mappdk_cmd.kl`，`MOVEJ`/`MOVEP` 解析軸數那段 | 動作指令最多 9 軸 |
| server tag 只取 1 個字元 | `mappdk_comm.kl`，`OPEN_COMM` 組 tag 字串那段 | 只能用 S1 到 S9 |
| `setsysvar` 只吃 T/F | `mappdk_cmd.kl` 的 `SET_SYS_VAR` | 數值型系統變數要用 `setsysvarnum`（擴充指令） |
| 回應是 `STRING[254]` | `mappdk_server.kl`，`resp` 變數宣告 | 單次回應長度上限 |
| 單一連線、同步阻塞 | `mappdk_server.kl`，`OPEN_COMM`/主迴圈 | 一支 server 同時只能接一個客戶端；動作指令會卡到動作完成。第二條連線用 logger，見[兩條連線](connections.md) |
| `DIN[]` 對使用者程式唯讀 | KAREL 語言層級 | 沒辦法從使用者 KAREL 程式寫入/模擬 DI，編譯期就被 ktrans 擋下，跟有沒有開 TP 的 SIM 模式無關，這條路已經放棄，見下方 |

## DI 沒辦法寫入/模擬

試過加一個 `setdin` 指令，KAREL 端直接對 `DIN[din_num]` 賦值，跟已經
驗證能動的 `SET_DOUT`（`mappdk_cmd.kl`，寫 `DOUT[]`）用一樣的寫法，
差別只在 DIN 是輸入陣列。結果 `ktrans` 編譯期就直接拒絕：

```
This system Id is "write protected" from KAREL user programs.  Id: DIN
```

這不是「風險評估後暫緩」，是 KAREL 語言本身就不允許：`DIN[]` 對使用者
程式是唯讀的，跟 TP 上有沒有把那個點設成模擬（SIM）模式完全無關（連
編譯都過不了，根本不會跑到那一步）。DI 模擬只能透過 TP 操作面板本身
（如果該型號/版本支援），這個套件的 driver 這條路已經徹底放棄，
不要再嘗試同樣的寫法。

## RDO 超界會讓整支 server 中止

RDO 編號原本也只取 1 個字元，編號 10 以上會被截成第一位數而且不報錯。
本專案的 driver 改成讀到字串結尾，接上游 driver 時 Python 這邊會自己
套用舊上限。

**存取控制器沒有的 RDO 會讓整支 MAPPDK_SERVER 中止。** TP 上會看到

```
PRIO-002 端口號不正確
```

要按 RESET 再重跑 MAPPDK 才能恢復。KAREL 那邊擋不掉，`GET_PORT_VAL`
需要 `io_rdo` 常數，而加上 `IOSETUP` 環境之後會超出 ktrans 對指示詞加
環境總數的上限（見[擴充 driver](extending-the-driver.md#environment-的坑)）。
所以上限放在 Python：`protocol.MAX_RDO_NUM` 預設 8，也可以在建構
`FanucRobot` 時傳 `max_rdo` 調整。DI 和 DO 也有同樣的風險。

---
*最後更新：2026-08-31*
