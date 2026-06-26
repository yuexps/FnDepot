# USB 继电器温控系统 (yuexps-usb-fan)

飞牛 NAS (FNOS) 的 USB 继电器 温控程序。

### 自定义配置说明
应用运行后，会在持久化目录`/var/apps/yuexps-usb-fan/var/config.json`生成配置文件。可通过 Web 界面直接修改，也可以编辑 JSON 文件后重启生效：

| 参数名 | 默认值 | 作用说明 |
| :--- | :--- | :--- |
| `serial_port` | `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` | 自定义 USB 串口硬件设备地址 |
| `baud_rate` | `9600` | 串口通信波特率 |
| `ceiling` | `55.0` | 自动温控开启上限温度，单位摄氏度 |
| `floor` | `50.0` | 自动温控关闭下限温度，单位摄氏度 |
| `mode` | `auto` | 默认启动模式，auto 为自动温控，manual 为手动控制 |
| `poll_interval` | `3` | 后端温度采样与温控循环周期，单位秒 |
| `temp_path` | `hwmon:coretemp:temp1_input` | 温度传感器路径，支持 hwmon 格式（如 `hwmon:coretemp:temp1_input`）和 thermal_zone 绝对路径（如 `/sys/class/thermal/thermal_zone0/temp`） |
| `has_feedback` | `true` | 是否支持反馈，true 为有反馈，false 为无反馈 |
| `op_close_nofeed` | `A00100A1` | 无反馈关闭指令十六进制数据帧 |
| `op_open_nofeed` | `A00101A2` | 无反馈开启指令十六进制数据帧 |
| `op_close_feed` | `A00102A3` | 有反馈关闭指令十六进制数据帧 |
| `op_open_feed` | `A00103A4` | 有反馈开启指令十六进制数据帧 |
| `op_toggle_feed` | `A00104A5` | 状态取反指令十六进制数据帧 |
| `op_query` | `A00105A6` | 硬件状态查询指令十六进制数据帧 |
| `status_on` | `A00101A2` | 代表开启状态的硬件回执特征数据帧 |
| `status_off` | `A00100A1` | 代表关闭状态的硬件回执特征数据帧 |

### 硬件与系统参数获取说明

（串口设备、温度传感器）均可直接在 Web 界面配置弹窗中自动扫描选择！

1. **串口设备路径**：
   - **动态路径（不推荐长期使用）**：插入 USB 继电器后，在终端执行 `ls /dev/ttyUSB*` 或 `ls /dev/ttyACM*`。常见识别结果为 `/dev/ttyUSB0`。该路径容易因重启或插拔发生漂移。
   - **固定路径（推荐）**：在终端执行 `ls /dev/serial/by-id/`，找到如 `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` 的唯一 ID 路径。使用该路径可以保证重启或插拔后设备地址不发生改变。

2. **温度文件路径**：

   - **hwmon 格式（推荐）**
     - 在终端执行 `ls /sys/class/hwmon/` 查看 hwmon 设备列表。
     - 执行 `cat /sys/class/hwmon/hwmon*/name` 查看各设备驱动名称，如 `coretemp`（Intel CPU）、`k10temp`（AMD CPU）、`drivetemp`（硬盘）、`nvme`（NVMe 硬盘）、`amdgpu`（AMD 显卡）等。
     - 对于有多个子传感器的设备（如 `drivetemp`、`nvme`），执行 `cat /sys/class/hwmon/hwmonX/temp*_label` 可查看各子传感器的标签。
     - 确定后，在配置文件的 `temp_path` 中填入 `hwmon:驱动名:tempX_input` 格式，例如 `hwmon:coretemp:temp1_input`。

   - **thermal_zone 格式**
     - 在终端执行 `cat /sys/class/thermal/thermal_zone*/type` 查看各温度传感器类型。
     - 寻找需要监控的传感器名称，如 CPU 相关的 `x86_pkg_temp` 或其他主板传感器。
     - 确定对应编号后，将完整路径 `/sys/class/thermal/thermal_zoneX/temp`（X 为传感器编号）填入配置文件的 `temp_path` 中，例如 `/sys/class/thermal/thermal_zone0/temp`。

3. **继电器指令帧与回执帧**：
   - 查阅商家提供的产品通信协议文档，获取开启、关闭、状态查询以及状态回执的十六进制报文。
   - 或者使用串口抓包工具，在 Windows 下捕获配套控制软件发送与接收的十六进制原始数据。

## 构建与部署

### 1. 一键编译打包
在 Windows 根目录下双击运行：
**`build.cmd`**

脚本会自动进行 Go 交叉编译并调用 `fnpack` 工具，生成安装包：
**`yuexps-usb-fan.fpk`**

### 2. FNOS 部署
登录 FNOS 后台 -> 进入“应用中心” -> 手动安装导入生成的 `yuexps-usb-fan.fpk` 即可。
