"""天气业务由 service 显式调用，返回固定数据，不请求外部天气服务。"""


def get_weather(city: str) -> dict:
    # 不同城市仅改变 city 字段，其余值都是预设教学数据。
    return {

        "city": city,

        "condition": "晴",

        "temperature": 26,

        "dataSource": "模拟数据，非实时天气",
    }