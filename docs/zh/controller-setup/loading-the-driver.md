# 載入 driver

要上傳的檔案都在 [driver/upload/](../../../driver/upload/)，
不用去 `driver/` 上一層找 `.kl` 原始碼，那些是給要改程式的人看的，
不能直接上傳到控制器。

兩個 `.pc` 檔案依控制器軟體版本分成不同子資料夾（`v9.40/`、`v9.30/`
……），版本編錯的 `.pc` 上傳到控制器會出現
`INTP-320 Unassigned built-in`（未定義的內置函數）這種錯誤，所以先
確認你控制器的版本（`菜單` → `NEXT` → `STATUS` → `Version ID`，看
「Default Personality」那一行），再對應選子資料夾。三個 `.ls` 檔案
不是編譯出來的，跟版本無關，放在 `upload/` 最上層，每個版本共用。

| 檔案 | 說明 |
| --- | --- |
| `<版本>/mappdk_server.pc` | 主 server |
| `<版本>/mappdk_logger.pc` | 第二條連線（不需要 S7 的話可以不載） |
| `mappdk.ls` | TP 主程式，會啟動上面兩支 |
| `mappdk_move.ls` | 動作指令用 |
| `mappdk_movel.ls` | 直線動作指令用 |

## 檔案要放到 UD1:

workcell 目錄下的 `Robot_1\UD1\` 在虛擬控制器裡就是 **UD1:** 裝置，
等於一支永遠插著的隨身碟。不用真的 USB 也不用 FTP，把對應版本的兩個
`.pc` 檔案，加上共用的三個 `.ls` 檔案，從 `driver/upload/` 複製進
`Robot_1\UD1\`（攤平放，`UD1:` 裡沒有子資料夾，版本分類只存在於這個
repo 裡）。

ROBOGUIDE 已經開著的話，要重開 workcell 才看得到新複製進去的檔案。

## 從 TP 載入

`菜單` → `文件` → `文件` → `功能` → `設置設備` → 選 `UD1:` →
遊標移到檔名 → `ENTER` → `加載`。問要不要覆寫選 YES。

**先載兩個 `.pc`，再載三個 `.ls`。** 順序錯了不會出事，但養成這個
順序比較不容易漏掉檔案。

### `.ls` 載不進去

`.ls` 是 ASCII 原始碼，要有 **ASCII Upload（R507）** 選項，沒有的話
會出現 `文件加載錯誤` 或 `選項未安裝`。

沒有這個選項的話，改走 ROBOGUIDE 自己的翻譯器（介面是英文，不受 TP
語言影響）：Cell Browser → `FanucRobot Controller` → `Programs` →
右鍵 → **Load Program** → 選 `.ls`，ROBOGUIDE 會自動翻成 `.tp` 載入。

## 確認載進去了

`一覽` → `類型` → `全部`，應該看到：

```
MAPPDK           [MAPPDK MAIN]
MAPPDK_LOGGER  PC
MAPPDK_MOVE
MAPPDK_MOVEL
MAPPDK_SERVER  PC
```

（沒載 S7 的話不會有 `MAPPDK_LOGGER` 這行，正常。）

標 `PC` 的是 KAREL 編譯產物，只會出現在 `KAREL程序` 分類；其他幾支
是 TP 程序，會出現在 `TP程序` 分類。

載完，繼續看[執行](running.md)。

---
*最後更新：2026-09-05*
