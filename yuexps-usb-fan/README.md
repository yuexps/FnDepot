# USB 继电器温控系统 (yuexps-usb-fan)

飞牛 NAS (FNOS) 的 USB 继电器 温控程序。

### 自定义配置说明
应用运行后，会在持久化目录（FNOS 环境为 `/var/apps/yuexps-usb-fan/var/config.json`，本地运行为同级 `config.json`）生成配置文件。你可以直接编辑该 JSON 文件来自定义参数（修改保存后，重启应用服务即可生效）：

| 参数名 | 默认值 | 作用说明 |
| :--- | :--- | :--- |
| `serial_port` | `/dev/ttyUSB0` | 自定义 USB 串口硬件设备地址 |
| `baud_rate` | `9600` | 串口通信波特率 |
| `ceiling` | `55.0` | 自动温控开启上限温度，单位摄氏度 |
| `floor` | `50.0` | 自动温控关闭下限温度，单位摄氏度 |
| `mode` | `auto` | 默认启动模式，auto 为自动温控，manual 为手动控制 |
| `poll_interval` | `3` | 后端温度采样与温控循环周期，单位秒 |
| `temp_path` | `/sys/class/thermal/thermal_zone1/temp` | 温度文件路径 |
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

1. **串口设备路径**：
   - 插入 USB 继电器后，在终端执行 `ls /dev/ttyUSB*` 或 `ls /dev/ttyACM*`。
   - 常见识别结果为 `/dev/ttyUSB0`。

2. **温度文件路径**：
   - 在终端执行 `cat /sys/class/thermal/thermal_zone*/type` 查看各温度传感器类型。
   - 寻找需要监控的传感器名称，如 CPU 相关的 `x86_pkg_temp` 或其他主板传感器。
   - 确定对应编号后，其温度路径即为 `/sys/class/thermal/thermal_zoneX/temp`，其中 X 代表对应传感器的编号。

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
