# conversation
在HA里使用的官方语音助手修改增强版


> 官方文档：https://www.home-assistant.io/integrations/conversation/


## 云音乐指令（需要配合云音乐播放器使用）

- 我想听xxx的歌
- 播放电台xxx
- 播放歌单xxx
- 播放歌曲xxx
- 播放专辑xxx
- 下一曲
- 上一曲
- 播放音乐
- 暂停音乐
- 声音小点、小点声音、小一点声音、声音小一点
- 声音大点、大点声音、大一点声音、声音大一点

## 开关指令

**开关设备**

- 打开xxx、开启xxx、启动xxx
- 关闭xxx、关掉xxx、关上xxx
- 切换xxx


**开关所有设备，以上操作加如下命令，控制所有灯和开关**

- 所有灯、所有的灯、全部灯、全部的灯
- 所有开关、所有的开关、全部开关、全部的开关

## 摄像监控

- 查看xxx的画面

## 执行脚本
- 脚本名称=语音文本

## node-red 和 自动化
- 监听ha_voice_text_event事件
- text: 语音文本

## 更新日志

### v1.3
- 解决不能操作所有灯和开关的问题
- 加入查看摄像监控的画面

### v1.2
- 加入单独的聊天界面
- 支持`python_script.conversation`服务，接收`text`参数
- 优化聊天界面登录逻辑

### v1.1
- 优化代码结构
- 增加重载服务（修改配置不用重启）

### v1.0
- 当语音文本与脚本名称一致时，则触发脚本
- 语音文本匹配多个内容时，脚本名称使用=号分隔
- 定义ha_voice_text_event事件发送文本
- 语音支持：添加xxx到我的购物单
- 语音支持：我的购物单上有什么
- 集成聊天机器人