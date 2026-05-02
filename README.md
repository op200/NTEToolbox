# 异环工具箱

基于 MaaFramework 的异环自动化工具

完全以后台运行为目的开发，不用担心抢占窗口焦点和键鼠

*模板自 [MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate/tree/e454642639415a2c7068b4121c9f61641ec88569)*

## 下载与使用

### 下载

在 [Release](https://github.com/op200/NTEToolbox/releases) 中下载最新版本的压缩包

解压后即可使用

### GUI

目前会自动打包 MFAA 和 MXU 两种 GUI，觉得哪个好用就用哪个

* #### MFAA

  启动时会自动判断 [.NET](https://dotnet.microsoft.com) 和 [C++](https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist) 运行时  
  若电脑中没有对应运行时，需按 GUI 给出的提示在微软官网下载或 GUI 自动下载

* #### MXU

  体积小，执行效率也比 MFAA 高  
  如果觉得 MFAA 钓鱼时溜鱼跟随不及时，最好换用这个 GUI

### 启动

打开文件夹内对应的 GUI 的 exe 文件（Windows）即可启动

**因为要支持后台运行，所以必须使用管理员模式打开，如果嫌每次都要右键exe麻烦，可以在属性里把该exe设为 `以管理员身份运行此程序`**

**仅支持游戏分辨率比例 16:9**，内部缩放到 720p 处理，所以设置 720p 以上并不会提高识别精度

### 依赖

依赖 Python，自行安装 [Python 3.14](https://www.python.org/downloads/release/python-3144/) 或更高版本，Windows 用户安装时记得勾选添加到 PATH

需要安装 Python 包 `maafw`  
（安装并更新命令: `pip install -U maafw`）

*如果发现 GUI 中任务执行到一半直接失败，那么大概是调用 Python 失败*

## 功能

### 自动钓鱼 🎣

完全可用，响应很快，钓到饵用完判断为完成

*没做自动换饵（感觉这个功能没啥用）*

### 弹钢琴 🎹

游戏内先打开钢琴界面，GUI 选项中输入 MIDI 文件的路径，会读取第一个乐器，自动弹钢琴

解码 MIDI 文件依赖 [music21](https://github.com/cuthbertLab/music21)  
（安装并更新命令: `pip install -U music21`）
