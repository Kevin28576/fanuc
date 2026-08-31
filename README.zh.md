# fanuc

*[English](README.md)*

> 本專案受下方論文、期刊、研討會等啟發：
> - [陳彥甫（2020）。數位孿生於機械手臂虛實整合之研究（碩士論文）。淡江大學。DOI: 10.6846/TKU.2020.00496](https://doi.org/10.6846/TKU.2020.00496)
> - [陳誼玲（2021）。遠端語音監控製造系統（碩士論文）。嶺東科技大學。](https://www.airitilibrary.com/Article/Detail?DocID=U0103-0906202110200700)
> - [鍾杰儒（2019）。應用機械視覺於機械手臂自動化系統之設計（碩士論文）。義守大學。](https://www.airitilibrary.com/Article/Detail?DocID=U0074-2008201906045900)
> - [施志軒、林宛昀。〈基於大型語言模型之智慧機器人製造單元助理〉。《機械工業雜誌》第509期（2025）：頁20-32。DOI: 10.30256/JIM.202508_(509).0006](https://doi.org/10.30256/JIM.202508_%28509%29.0006)
> - [黃勇益、王朝仕、粘昰薪、陳冠叡。〈機械手臂資訊擷取與檢測應用〉。收入《TANET2019 臺灣網際網路研討會》，頁1059-1063。國立中山大學，2019。DOI: 10.6924/TANET.201909.0192](https://doi.org/10.6924/TANET.201909.0192)
> - [杜彥頤。〈工研院機器手臂動態控制器－使用者自訂函數介紹〉。《機械工業雜誌》第400期（2016）：頁17-28。DOI: 10.30256/JIM.201607_(400).0004](https://doi.org/10.30256/JIM.201607_%28400%29.0004)

## 測試環境

本專案使用的機械手臂為 FANUC [ER-4iA](https://www.fanucamerica.com/products/robot/er-4ia)
（Education Series），控制器為 R-30iB Mate Plus，完整規格見
[FANUC 官網規格頁](https://www.fanucamerica.com/products/robot/er-4ia#specifications)。

實機測試環境由[萬能科技大學資訊工程系暨研究所、電資研究所](https://www.csie.vnu.edu.tw/)
提供機器使用空間與相關資源，特此致謝。

[![PyPI](https://img.shields.io/pypi/v/fanuc)](https://pypi.org/project/fanuc/)
[![Downloads](https://img.shields.io/pypi/dm/fanuc)](https://pypistats.org/packages/fanuc)
[![Python versions](https://img.shields.io/pypi/pyversions/fanuc)](https://pypi.org/project/fanuc/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![CI](https://github.com/Kevin28576/fanuc/actions/workflows/ci.yml/badge.svg)](https://github.com/Kevin28576/fanuc/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Kevin28576/fanuc/branch/main/graph/badge.svg)](https://codecov.io/gh/Kevin28576/fanuc)

用 Python 操作 FANUC 機器人的工具，底層是 MAPPDK 的 KAREL driver。可以讀寫
目前位置、關節角度、暫存器、數位 I/O，控制夾爪開合，下移動指令、跑 TP
程式、讀警報狀態，也附一個能直接在終端機用的 `fanuc` 指令列工具。

這個 repo 分兩個部分：

- **`src/fanuc/`**：Python 套件，透過一般 TCP socket 跟控制器通訊
- **`driver/`**：跑在控制器上的 KAREL/TP driver，負責通訊的另一端

![Python 套件跟控制器之間的通訊協定](https://raw.githubusercontent.com/Kevin28576/fanuc/main/media/CommProtocol.svg)

> [!WARNING]
> 強烈建議先在 ROBOGUIDE 虛擬控制器上開發、測試，確認邏輯沒問題之後，
> 再把 `host` 換成控制器 IP 接上真實的機器人，避免程式邏輯上的失誤直接
> 在實機上發生無法預期的狀況。

> [!CAUTION]
> MAPPDK 的傳輸協定完全沒有認證、也沒有加密，就是明文的 TCP socket。
> 任何人只要連得到控制器的 port（18735，如果有設 S7 的話還有
> 18736），就能送出移動指令、寫暫存器、寫系統變數，不需要任何登入。
> 這是 FANUC MAPPDK driver 本身的設計限制，不是這個套件或
> `driver/` 裡的 KAREL 程式能靠軟體修掉的。**絕對不要把這兩個 port
> 暴露在不受信任的網路上。** 控制器要放在獨立、只給機台使用的網段，
> 不要連到一般辦公室/產線網段，更不能連到外網，能連到那個網段，
> 就等於能實際碰到這台機器人。換掉預設的 port 不會多一層認證，
> 但做起來不難，也值得做，見
> [docs/zh/controller-setup/server-tags.md](docs/zh/controller-setup/server-tags.md#改用非預設的-port)。

## 目錄

- [測試環境](#測試環境)
- [安裝](#安裝)
- [快速開始](#快速開始)
- [指令列](#指令列)
- [Python API](#python-api)
  - [夾爪](#夾爪)
  - [暫存器與狀態](#暫存器與狀態)
  - [例外](#例外)
  - [動作中查位置](#動作中查位置)
  - [RobotApp 任務框架](#robotapp-任務框架)
- [架構](#架構)
- [driver 支援的指令](#driver-支援的指令)
- [driver/ 目錄](#driver-目錄)
- [目錄結構](#目錄結構)
- [版本紀錄](#版本紀錄)
- [授權](#授權)

## 安裝

控制器那邊要先設定好（一次性設定），見
[docs/zh/controller-setup.md](docs/zh/controller-setup.md)。設定好之後裝套件：

```
pip install -e .
```

## 快速開始

```python
from fanuc import FanucRobot

with FanucRobot(host="127.0.0.1") as robot:
    print(robot.get_curpos().format())        # 讀目前的直角座標
    robot.move_joint([0, 0, 0, 0, -90, 0], velocity=25)
```

連線、讀位置、移動，這三件事就是最基本的使用方式。夾爪、暫存器、
例外處理這些進階用法看下面的 [Python API](#python-api)。

更多用法看 [examples/](examples/README.md)，每支腳本只示範一個功能，跑起來
會印出實際送給控制器的指令跟結果，比文件更貼近真實輸出：

| 腳本 | 示範的功能 |
| --- | --- |
| [demo.py](examples/demo.py) | 連線、讀狀態、移動、讀寫 DOUT（最小示範） |
| [read_position.py](examples/read_position.py) | 讀目前位置（姿態、關節角度） |
| [home_position.py](examples/home_position.py) | home 姿態怎麼設定、自訂、實際移動過去 |
| [gripper_control.py](examples/gripper_control.py) | 雙訊號夾爪：開、合、重置、讀狀態 |
| [check_reachability.py](examples/check_reachability.py) | 動作前先檢查關節/直角座標合不合法 |
| [registers_io.py](examples/registers_io.py) | 讀寫 R[n]、PR[n]、SR[n]、關節型位置暫存器、DI[n]、系統變數 |
| [raw_command.py](examples/raw_command.py) | 直接送原始指令字串、讀寫通用 RDO |
| [power_reading.py](examples/power_reading.py) | 讀取連線機器的瞬時功率 |
| [alarm_status.py](examples/alarm_status.py) | 讀最近一筆警報（完整內容） |
| [call_prog.py](examples/call_prog.py) | 呼叫 TP 程式的用法與注意事項 |
| [robot_app.py](examples/robot_app.py) | `RobotApp` 任務框架的生命週期 |
| [record_waypoints.py](examples/record_waypoints.py) | 手動移動、按 Enter 錄製點位 |
| [move_sequence.py](examples/move_sequence.py) | 讀點位 JSON，依序執行（含執行前檢查） |
| [trace_motion.py](examples/trace_motion.py) | 用 S7 連線背景記錄一段移動的實際軌跡 |

這裡列的都是英文版，想看中文版的話去
[examples/chinese/](examples/chinese/README.md)，同樣的檔名都找得到。

<!-- 另外還有一組實驗性、還沒經過太多驗證的範例，讓 LLM 加入迴圈、用聊天或
     語音控制機器人（請謹慎使用，跑之前先看各自的 README）：見
     examples/README.md#experimental-ai-control。尚未公開。 -->

## 指令列

| 指令 | 做什麼 |
| --- | --- |
| `fanuc connect set --host 192.168.1.10 --gripper-travel 1s` | 存連線設定 |
| `fanuc connect show` | 看目前存的連線設定 |
| `fanuc connect clear` | 清除，改回內建預設值 |
| `fanuc pos` | 讀目前位置 |
| `fanuc watch -i 0.2` | 持續顯示位置 |
| `fanuc status` | driver 版本、速度倍率、最近警報 |
| `fanuc io get rdo 7` | 讀 RDO[7] |
| `fanuc io set do 1 true` | 寫 DO[1] |
| `fanuc reg get r 1` | 讀 R[1] |
| `fanuc reg set r 1 100` | 寫 R[1] |
| `fanuc reg get pr 81` | 讀 PR[81] |
| `fanuc din 1` | 讀 DI[1] |
| `fanuc power` | 瞬時功率 |
| `fanuc move joint 0 0 0 0 -90 0 --confirm` | 移動機器人 |
| `fanuc call MY_PROG --confirm` | 執行 TP 程式 |

也可以用 `python -m fanuc`。`move`/`call` 沒加 `--confirm` 不會執行。

連線參數（`--host`、`--port` 等）用 `fanuc connect set` 存起來，之後的
指令就不用每次都帶。

### Shell TAB 補全（選用）

裝 `complete` extra，在 bash/zsh 底下註冊一次（寫進 shell 設定檔就永久
生效，只有第一次要手動跑）：

```bash
pip install -e ".[complete]"
eval "$(register-python-argcomplete fanuc)"
```

之後 `fanuc <TAB>` 會列出 `pos`/`watch`/`connect` 這些子指令，選項名稱
（`--host`、`--gripper-travel`）也補得出來。只支援 bash、zsh、tcsh、fish
（`argcomplete` 套件本身的限制），**PowerShell 沒有對應機制，裝了也不會
有效果**。不裝這個 extra 完全不影響 CLI 其他功能，純粹是少了 TAB 補全。

## Python API

暫存器與狀態：

```python
robot.get_reg(1)            # R[1]
robot.set_reg(1, 100)       # 整數
robot.set_reg(1, 1.5)       # 實數
robot.get_preg(81)          # PR[81]，回傳 Pose
robot.set_preg(81, [290, 0, 210, -180, 0, 0])
robot.get_din(1)            # DI[1]
robot.get_sys_var("$MCR.$GENOVERRIDE")
robot.get_override()        # 速度倍率 %
robot.get_alarm()           # Alarm(code, severity, cause_code, time, program, message)
result = robot.check_joint([45, -20, 15, 0, -45, 90])
if not result:
    print(result.describe())     # 例如 "不合法：J2=150.00 超出 -110.00~120.00"

robot.check_pose([400, 50, -100, -180, 0, 0])   # 這個直角座標到不到得了
```

`check_joint` 的合法性判斷走控制器內建的 `J_IN_RANGE`，不是自己維護一份
角度表，連 J2/J3 這類機構耦合限制都會一併考慮。失敗時另外拿
`fanuc.limits.DEFAULT_JOINT_LIMITS_DEG`（從 TP 讀出來的真實數字）逐軸
比對，`result.violations` 列出可能是哪一軸；如果每一軸單獨看都在範圍內，
代表是純粹的耦合限制，這張表指不出來，`describe()` 會照實說。

`check_pose` 跟 `movep` 用同一個 `CHECK_EPOS` 判斷可達性，是 movep
已經在正式環境驗證過的內建函式。沒有對應的軸級診斷，直角座標到不了
通常是逆向運動學無解，不像關節角度那樣能拆成單軸原因。

[examples/move_sequence.py](examples/move_sequence.py) 執行任何動作前，
會用 `check_joint` 把全部關節點位過一遍；`check_pose` 單獨的用法見
[examples/check_reachability.py](examples/check_reachability.py)。

### 夾爪

`ee_DO_num` 是單訊號夾爪：一個輸出直接對應開/合。氣壓夾爪常常不是這樣接的，
開跟合是兩條獨立訊號（例如 SCHUNK EGP），不是同一條訊號的正反，而且切換
之間要留最短休息時間，切太快可能損壞夾爪內部電子設備。這種接法用
`ee_open_num`/`ee_close_num`：

```python
with FanucRobot(host="127.0.0.1", ee_DO_type="RDO",
           ee_open_num=7, ee_close_num=8,
           gripper_travel="500ms") as robot:
    robot.gripper(True)          # 合，內部先清 open、休息、再設 close，
                                  # 送出後等 gripper_travel 才返回
    robot.gripper(False)         # 開
    robot.gripper_reset()        # 重置警報（開合訊號同時 True）
    robot.get_gripper()          # "idle" / "open" / "closed" / "reset"
```

**`ee_open_num`/`ee_close_num` 填哪個號碼，看你實際怎麼接線**：

- 不同夾爪、不同接法，開/合訊號對應到哪個 RO 都可能不一樣，請照你夾爪
  的接線說明書指定，不要照抄範例
- 上面範例的 RO7/RO8，是驗證環境（SCHUNK EGP，接在 EE Pinout）在實機
  上確認過的：RO7=ON、RO8=OFF 是開，RO7=OFF、RO8=ON 是關；換一顆夾爪
  就要重新確認

**`gripper_travel` 是必填的**，帶單位的字串，例如 `"2s"`、`"0.5s"`、
`"100ms"`：

- 只要設定了任何夾爪輸出（`ee_DO_num` 或 `ee_open_num`/`ee_close_num`），
  就一定要給 `gripper_travel`，不給的話建構 `FanucRobot()` 會直接丟
  `ValueError`
- 不接受裸數字（只寫 `2` 不行），單位打錯或漏打是常見的錯誤來源，
  乾脆強制要求寫清楚
- 意思是夾爪開闔一次實際要花的時間，跟訊號切換之間的休息時間
  （`GRIPPER_REST_S`，電氣特性，這類夾爪大致相近，套件內建）是兩回事：
  行程時間是爪子物理移動要花多久，看夾爪大小、氣壓、行程長短，每一顆
  都不一樣，沒有安全的通用預設值，要自己對照規格書或實際量測填寫
- `gripper()` 送出訊號後，會等滿這個時間才返回，確保函式返回的當下
  夾爪真的已經動作完成，接下來的動作（例如夾著工件離開）才不會撞上
  夾爪還沒走完行程的狀態

### 例外

分成幾類，不用去比對錯誤字串：

```python
from fanuc import ConnectionError_, UnreachableError

try:
    robot.move_pose([9999, 0, 0, 0, 0, 0])
except UnreachableError:
    ...     # 位置到不了，改目標值
except ConnectionError_:
    ...     # 連線斷了，重連
```

### 動作中查位置

driver 是同步阻塞的。送出 `movej` 之後那條連線會卡到動作結束，這期間查不了位置。
控制器上的 `MAPPDK_LOGGER` 就是為了這個，它是第二個 server，聽在別的 port：

```python
from fanuc import FanucRobot, DEFAULT_PORT, LOGGER_PORT

mover = FanucRobot(host="127.0.0.1", port=DEFAULT_PORT)   # S8，下動作指令
probe = FanucRobot(host="127.0.0.1", port=LOGGER_PORT)    # S7，同時查位置
```

兩個 port 的指令集一樣。控制器要另外設 S7，見
[docs/zh/protocol/connections.md](docs/zh/protocol/connections.md)。想要邊移動邊
記錄完整軌跡，直接用 `fanuc.MotionTracer`，見
[examples/trace_motion.py](examples/trace_motion.py)。

### RobotApp 任務框架

寫成可重複執行的任務（要被排程器、Web API 呼叫）時用 `RobotApp`，
介面對齊上游 fanucpy 的 `RobotApp`：子類別在 `__init__` 收下 `FanucRobot`，
`_main()` 自己處理連線與收尾，`run()` 把結果或例外包成 `AppResult`。

```python
from fanuc import FanucRobot, RobotApp

class MyApp(RobotApp):
    def __init__(self, robot):
        self.robot = robot

    def configure(self):
        pass  # 靜態設定，不連線

    def _main(self, **kwargs):
        self.robot.connect()
        try:
            ...
            return "done"
        finally:
            self.robot.disconnect()

app = MyApp(FanucRobot(host="127.0.0.1"))
app.configure()
result = app.run()
if not result:
    print(result.message)
```

完整範例見 [examples/robot_app.py](examples/robot_app.py)。

## 架構

沒有第三方相依，只用標準庫 `socket`。

```
src/fanuc/
├── cli.py         指令列
├── robot.py       高階 API
├── app.py         RobotApp 任務框架
├── protocol.py    指令字串的組裝與解析
├── transport.py   socket
├── types.py       Pose / Joints
└── exceptions.py  例外
```

protocol 層不碰 socket，所以指令格式可以離線測；`transport.py` 則是用
真的 loopback TCP server 測，不是靠 mock。`tests/` 有 220 個測試，
不需要 ROBOGUIDE 也不需要實機：

```
pytest
```

覆蓋率（要先裝 `dev` extra，`pip install -e ".[dev]"`）目前是行覆蓋率
與分支覆蓋率都 100%，代表離線就能走到每一條路徑（真的 socket、假物件、
mock），不是在說這份程式碼沒有 bug。目前各檔案的覆蓋率明細看
[codecov 面板](https://codecov.io/gh/Kevin28576/fanuc)，或本機自己跑：

```
pytest --cov=fanuc --cov-report=term-missing
```

加新指令的順序：先在 `protocol.py` 寫 `encode_*` / `parse_*` 加測試，再接 `robot.py`。

## driver 支援的指令

基本的移動、讀寫 I/O、讀位置這些原始 driver 就有；本專案另外加了 15 個
擴充指令（`ver`、`getreg`、`setreg`、`getpreg`、`setpreg`、`getdin`、
`getsysvar`、`getalarm`、`chkjnt`、`chkpos`、`setsysvarnum`、`getsreg`、
`setsreg`、`getjpreg`、`setjpreg`），全部都已經在實機驗證過，細節見
[docs/zh/protocol.md](docs/zh/protocol.md)。`getalarm` 目前只能讀最近一筆，
讀不到歷史，見該文件的說明。

連線時會送 `ver` 問版本，藉此判斷控制器上載入的是不是本專案的擴充版
driver。沒有的話 `robot.extended` 會是 `False`，呼叫擴充方法會直接說
需要載入本專案的 driver，不會丟一個看不懂的 `wrong-command`。

```python
robot.driver_version    # 'fanuc-driver 0.2.0'，沒載擴充版是 None
robot.extended          # True / False
```

指令格式、欄位寬度、driver 的限制都在 [docs/zh/protocol.md](docs/zh/protocol.md)。

想試新指令可以先用 `robot.send_raw("...")` 直接送字串。

## driver/ 目錄

控制器上跑的 KAREL 程式，原始碼、編譯產物、要上傳的檔案分開放：

| 想做什麼 | 看哪裡 |
| --- | --- |
| 把 driver 裝到控制器上 | [driver/upload/](driver/upload/README.md)，裡面 5 個檔案就是全部要上傳的東西 |
| 改 KAREL 程式碼、重新編譯 | [driver/README.md](driver/README.md) |
| 控制器端設定 tag、載入、驗證 | [docs/zh/controller-setup.md](docs/zh/controller-setup.md) |

driver 會佔用幾個暫存器跟座標系編號，workcell 裡用到同樣編號會被蓋掉：

| 資源 | 用途 |
| --- | --- |
| `UFRAME[8]`、`UTOOL[1]` | 座標系 |
| `R[81]` | 速度 |
| `R[82]` | 加速度 |
| `R[83]` | CNT |
| `PR[81]` | 位置 |

程式裡用 `fanuc.RESERVED` 可以拿到這份清單，細節見
[docs/zh/protocol/reserved-resources.md](docs/zh/protocol/reserved-resources.md)。

## 目錄結構

```
fanuc/
├── src/fanuc/   套件
├── examples/    範例腳本（英文，中文版在 examples/chinese/）
├── tests/       協定測試
├── driver/      KAREL 原始碼（driver/upload/ 是要上傳到控制器的檔案）
└── docs/        設定與協定文件（英文，docs/zh/ 是中文版，結構一一對應）
```

## 版本紀錄

見 [CHANGELOG.md](CHANGELOG.md)（英文，這份沒有另外做中文版）。

## 授權

Apache License 2.0，見 [LICENSE](LICENSE)。

`driver/` 的 KAREL 程式改自 [fanucpy](https://github.com/torayeff/fanucpy)
（Copyright Agajan Torayev，Apache-2.0），改了哪些見 [NOTICE](NOTICE)。


---
*最後更新：2026-08-31*
