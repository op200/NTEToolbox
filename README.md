# 异环工具箱

基于 MaaFramework 的异环自动化工具

完全以后台运行为目的开发，不用担心抢占窗口焦点和键鼠

*模板自 [MaaPracticeBoilerplate](https://github.com/MaaXYZ/MaaPracticeBoilerplate/tree/e454642639415a2c7068b4121c9f61641ec88569)*

## 下载与使用

目前会自动打包 MFAA 和 MXU 两种 GUI，觉得哪个好用就用哪个

**因为要支持后台运行，所以必须使用管理员模式打开，如果嫌每次都要右键exe麻烦，可以在属性里把该exe设为 `以管理员身份运行此程序`**

依赖 Python，自行安装 [Python 3.14](https://www.python.org/downloads/release/python-3144/) 或更高版本

## 功能

### 自动钓鱼  

完全可用，响应很快，钓到饵用完判断为完成

*没做自动换饵（感觉这个功能没啥用）*

### 弹钢琴

游戏内先打开钢琴界面，GUI 选项中输入 MIDI 文件的路径，会读取第一个乐器，自动弹钢琴

解码 MIDI 文件依赖 [music21](https://github.com/cuthbertLab/music21)  
（安装并更新命令: `pip install -U music21`）
