# 擴充指令

本專案在 `driver/mappdk_ext.kl` 加的，要載入本專案編譯的 `.pc` 才能用。
接到上游 driver 會收到 `wrong-command`。

| 指令 | 參數 | 回應 | 方法 |
| --- | --- | --- | --- |
| `ver` | 無 | `fanuc-driver 0.2.0` | 連線時自動送 |
| `getreg` | `:<5 位補零>` | 數值 | `get_reg()` |
| `setreg` | `:<5 位補零>:<值>` | `success` | `set_reg()` |
| `getpreg` | `:<5 位補零>` | 同 `curpos` | `get_preg()` |
| `setpreg` | `:<5 位補零>:<6 個值>` | `success` | `set_preg()` |
| `getdin` | `:<5 位補零>` | `0` / `1` | `get_din()` |
| `getsysvar` | `:<變數名>` | 數值 | `get_sys_var()` |
| `getalarm` | 無 | `id=..,sev=..,cause=..,time=..,prog=..,msg=..` | `get_alarm()` |
| `chkjnt` | `:<軸數>:<N 個值>` | `0` / `1` | `check_joint()` |
| `chkpos` | `:<6 個值>` | `0` / `1` | `check_pose()` |
| `setsysvarnum` | `:<變數名>:<值>` | `success` | `set_sys_var_num()` |
| `getsreg` | `:<5 位補零>` | 字串 | `get_sreg()` |
| `setsreg` | `:<5 位補零>:<值>` | `success` | `set_sreg()` |
| `getjpreg` | `:<5 位補零>` | 同 `curjpos` | `get_jpreg()` |
| `setjpreg` | `:<5 位補零>:<軸數>:<N 個值>` | `success` | `set_jpreg()` |

## 實機驗證狀態

`setsysvarnum`、`getsreg`/`setsreg`、`getjpreg`/`setjpreg` 都已經在
實機驗證過，可以用。`getalarm` 只能讀最近一筆，讀不到歷史，細節見下面。

## `setreg` / `getreg`

看值有沒有小數點決定寫整數暫存器還是實數暫存器，所以 `1` 和 `1.0` 不一樣。
Python 這邊用 `int` / `float` 區分，不做正規化。

## `setpreg` / `getpreg`

數值格式跟 `movep` 一樣。driver 會保留目前位置的 configuration，
只蓋掉 XYZWPR 六個值。config 沒初始化的話後面的動作會算不出解。

## `getsysvar`

先當整數讀，失敗再當實數讀。速度倍率、UFRAME/UTOOL 編號這些都靠它，
不用每一項各寫一支常式。

## `getalarm`

**只能讀最近一筆，讀不到歷史。** `ERR_DATA` 的參數形式上是輸入序號，
但實測傳不同序號進去，回來的都是同一筆，跟這個做法有關的完整除錯
經過見[疑難排解](debugging-notes.md#警報歷史讀不到)。目前這個做法
已經拿掉，要看完整警報歷史，現階段直接去 TP 的 `报警` → `履历` 畫面。

訊息可能含逗號，所以放最後一欄，解析時只切前五個逗號。`ERR_DATA`
一次會拿到 7 個欄位，除了代碼/嚴重度/訊息，`cause`（原因代碼）、
`time`（時間戳）、`prog`（發生時的程式名稱）也一起傳出來，
`FanucRobot.get_alarm()` 回傳的是具名的 `Alarm` 型別。`time` 的實際
單位/起始點沒有查證過官方文件，先當成不透明的數字看待，不要拿來做
日期運算。範例見 [examples/alarm_status.py](../../../examples/chinese/alarm_status.py)。

## `chkjnt`

走 KAREL 內建的 `J_IN_RANGE`，不是自己維護一份角度上下限表。好處是連
J2/J3 這類機構耦合限制都會一併考慮，是控制器自己的判斷邏輯；壞處是
只能問「這個位置合不合法」，問不出實際的限位數值是多少。純查詢，
不會讓機器人動。

`J_IN_RANGE` 要吃 `JOINTPOS6` 型別，不能用通用的 `JOINTPOS`，否則會丟
`INTP-311 参数还没有设定`，而且是在整支 server 卡住、不會回應也不會
報連線錯誤那種丟法（Python 端只會 timeout）。`MOVEJ` 常式一直是用
`JOINTPOS6`，這裡跟著一致就没事。

`J_IN_RANGE` 只回傳合不合法，不會說是哪一軸。Python 端的
`FanucRobot.check_joint()` 失敗時會另外拿
`fanuc.limits.DEFAULT_JOINT_LIMITS_DEG` 逐軸比對，這張表只是診斷輔助，
不是合法性判斷依據，`J_IN_RANGE` 才是。兩者可能不一致：每一軸單獨看
都在範圍內，但 `J_IN_RANGE` 還是說不合法，代表是純粹的機構耦合限制
（例如 J2/J3），這張表算不出來，`check_joint()` 的結果會如實回報找不到
違規軸，不會硬掰一個出來。

## `chkpos`

跟 `movep`（`mappdk_cmd.kl` 的 `MOVEP`）用同一個 `CHECK_EPOS` 判斷
可達性，是 movep 已經在正式環境驗證過的內建函式，不是新的、沒試過
的東西，所以這支沒有像 `chkjnt` 那樣先出過事才找到正確用法。差別是
只算目標點本身的逆向運動學，不會模擬整段路徑，理論上到得了的兩個
端點，直線插值路徑中間仍可能因為姿態組態切換而失敗，`chkpos`
抓不到這種情況。

## `getjpreg` / `setjpreg`

第一版實機測試時整個卡住過，修法見
[疑難排解](debugging-notes.md#getjpreg-第一版卡住)。

---
*最後更新：2026-08-31*
