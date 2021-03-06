import logging, re, aiohttp
from homeassistant.helpers import intent
import homeassistant.config as conf_util
from homeassistant.helpers import template

_LOGGER = logging.getLogger(__name__)

DOMAIN = "conversation"
DATA_AGENT = "conversation_agent"
DATA_CONFIG = "conversation_config"

def text_start(findText, text):
    return text.find(findText,0,len(findText)) >= 0

class Voice():

    def __init__(self, hass):
        self.hass = hass
        hass.services.async_register(DOMAIN, 'reload', self.reload)

    # 解析模板
    def template(self, message):
        tpl = template.Template(message, self.hass)
        return tpl.async_render(None)

    # 返回意图结果
    def intent_result(self, message):
        intent_result = intent.IntentResponse()
        intent_result.async_set_speech(message)
        return intent_result

    # 重新加载配置
    async def reload(self, service):
        hass = self.hass
        # 读取配置
        hass.data[DATA_CONFIG] = await conf_util.async_hass_config_yaml(hass)
        # 清除agent
        hass.data[DATA_AGENT] = None

    # 触发事件
    def fire_text(self, text):
        hass = self.hass
        # 去掉前后标点符号
        _text = text.strip(' 。，、＇：∶；?‘’“”〝〞ˆˇ﹕︰﹔﹖﹑·¨….¸;！´？！～—ˉ｜‖＂〃｀@﹫¡¿﹏﹋﹌︴々﹟#﹩$﹠&﹪%*﹡﹢﹦﹤‐￣¯―﹨ˆ˜﹍﹎+=<­­＿_-\ˇ~﹉﹊（）〈〉‹›﹛﹜『』〖〗［］《》〔〕{}「」【】︵︷︿︹︽_﹁﹃︻︶︸﹀︺︾ˉ﹂﹄︼')    
        # 发送事件，共享给其他组件
        hass.bus.fire('ha_voice_text_event', {
            'text': _text
        })
        # 调用python_script.conversation
        if hass.services.has_service('python_script', 'conversation'):
            hass.async_create_task(hass.services.async_call('python_script', 'conversation', {
                'text': _text
            }))
        return _text

    # 查看设备
    def query_device(self, text):
        hass = self.hass
        device_type = None
        if text == '查看全部设备':
            device_type = ''
        elif text == '查看全部灯':
            device_type = '.light'
        elif text == '查看全部传感器':
            device_type = '.sensor'
        elif text == '查看全部开关':
            device_type = '.switch'
        elif text == '查看全部脚本':
            device_type = '.script'
        elif text == '查看全部自动化':
            device_type = '.automation'
        elif text == '查看全部场景':
            device_type = '.scene'

        if device_type is not None:
            return self.intent_result(self.template('''
                <table border cellpadding="5" style="border-collapse: collapse;">
                    <tr><th>名称</th><th>状态</th><th>操作</th></tr>
                    {% for state in states''' + device_type + ''' -%}
                    <tr>
                        <td>{{state.attributes.friendly_name}}</td>
                        <td>{{state.state}}</td>                        
                        <td>
                            {% if 'light.' in state.entity_id or 
                                  'switch.' in state.entity_id or
                                  'script.' in state.entity_id or
                                  'automation.' in state.entity_id or
                                  'scene.' in state.entity_id -%}
                                <a onclick="triggerDevice('{{state.entity_id}}', '正在执行', `{{state.attributes.friendly_name}}`)" style="color:#03a9f4;">触发</a>
                            {%- else -%}
                 
                            {%- endif %}
                        </td>
                    </tr>
                    {%- endfor %}
                </table>
            '''))
        return None

    # 执行动作
    async def execute_action(self, text):
        hass = self.hass
        if text == '重新加载配置':
            self.reload()
            return self.intent_result("重新加载配置成功")

        # 如果有查询到设备，则返回
        device_result = self.query_device(text)
        if device_result is not None:
            return device_result

        # 遍历所有实体
        states = hass.states.async_all()
        for state in states:
            entity_id = state.entity_id
            attributes = state.attributes
            state_value = state.state
            friendly_name = attributes.get('friendly_name')
            # 执行自定义脚本
            if entity_id.find('script.') == 0:
                cmd = friendly_name.split('=')
                if cmd.count(text) > 0:
                    arr = entity_id.split('.')
                    _LOGGER.info('执行脚本：' + entity_id)
                    await hass.services.async_call(arr[0], arr[1])
                    return self.intent_result("正在执行自定义脚本：" + entity_id)
            # 查询设备状态
            if friendly_name is not None:
                friendly_name_lower = friendly_name.lower()
                if text.lower() == friendly_name_lower + '的状态':
                    return self.intent_result(friendly_name + '的状态：' + state.state)
                # 查询设备属性
                if text.lower() == friendly_name_lower + '的属性':
                    message = self.template('''
                    {% set entity_id = "''' + entity_id + '''" -%}
                    <table border cellpadding="5" style="border-collapse: collapse;">
                        <tr>
                            <th>{{entity_id}}</th>
                            <th>{{states(entity_id)}}</th>
                        </tr>
                        {% for state in states[entity_id].attributes -%}
                        <tr>
                            <td>{{state}}</td>
                            <td>{{states[entity_id].attributes[state]}}</td>
                        </tr>  
                        {%- endfor %}
                    </table>
                    ''')
                    return self.intent_result(message)
                # 查询摄像监控画面
                if text.lower() == '查看' + friendly_name_lower + '的画面':
                    return self.intent_result(self.template('''
                    {% set image = states['camera.generic_camera'].attributes['entity_picture'] %}
                    <a href="{{ image }}" target="_blank">  <img src="{{ image }}" style="max-width:100%;" /> </a>
                    '''))

        return None

    # 执行开关
    async def execute_switch(self, _text):
        hass = self.hass
        intent_type = ''
        service_type = ''
        if text_start('打开',_text) or text_start('开启',_text) or text_start('启动',_text):
            intent_type = 'HassTurnOn'
            service_type = 'turn_on'
            if '打开' in _text:
                _name = _text.split('打开')[1]
            elif '开启' in _text:
                _name = _text.split('开启')[1]
            elif '启动' in _text:
                _name = _text.split('启动')[1]
        elif text_start('关闭',_text) or text_start('关掉',_text) or text_start('关上',_text):
            intent_type = 'HassTurnOff'
            service_type = 'turn_off'
            if '关闭' in _text:
                _name = _text.split('关闭')[1]
            elif '关掉' in _text:
                _name = _text.split('关掉')[1]
            elif '关上' in _text:
                _name = _text.split('关上')[1]            
        elif text_start('切换', _text):
            intent_type = 'HassToggle'
            service_type = 'toggle'
            _name = _text.split('切换')[1]
        # 默认的开关操作
        if intent_type != '':
            # 操作所有灯和开关
            if _name == '所有灯' or _name == '所有的灯' or _name == '全部灯' or _name == '全部的灯':
                await hass.services.async_call('light', service_type, {
                    'entity_id': self.template('{% for state in states.light -%}{{ state.entity_id }},{%- endfor %}').strip(',')
                })
                return self.intent_result("正在" + _text + self.template('''
                    <hr />
                    <table border cellpadding="5" style="border-collapse: collapse;">
                        <tr><th>名称</th><th>状态</th></tr>
                        {% for state in states.light -%}
                        <tr>
                            <td>{{state.attributes.friendly_name}}</td>
                            <td>{{state.state}}</td>  
                        </tr>
                    </table>
                '''))
            elif _name == '所有开关' or _name == '所有的开关' or _name == '全部开关' or _name == '全部的开关':
                await hass.services.async_call('switch', service_type, {
                    'entity_id': self.template('{% for state in states.switch -%}{{ state.entity_id }},{%- endfor %}').strip(',')
                })
                return self.intent_result("正在" + _text + self.template('''
                    <hr />
                    <table border cellpadding="5" style="border-collapse: collapse;">
                        <tr><th>名称</th><th>状态</th></tr>
                        {% for state in states.switch -%}
                        <tr>
                            <td>{{state.attributes.friendly_name}}</td>
                            <td>{{state.state}}</td>  
                        </tr>
                    </table>
                '''))
            else:
                await intent.async_handle(hass, DOMAIN, intent_type, {'name': {'value': _name}})
            return self.intent_result("正在" + _text)
        return None

    # 错误信息处理
    def error_msg(self, err_msg):
        # 没有找到设备
        if 'Unable to find an entity called' in err_msg:
            err_msg = err_msg.replace('Unable to find an entity called', '没有找到这个设备：')
        return err_msg

    # 聊天机器人
    async def chat_robot(self, text):
        message = "对不起，我不明白"
        try:
            async with aiohttp.request('GET','https://api.ownthink.com/bot?appid=xiaosi&spoken=' + text) as r:
                res = await r.json(content_type=None)
                _LOGGER.info(res)
                message = res['data']['info']['text']
        except Exception as e:
            _LOGGER.info(e)        
        return message
