"""天气服务：QWeather(和风) + Open-Meteo 双 Provider，归一化输出，带本地缓存。

归一化 schema（前端统一消费）：
{
  "city": "北京",
  "provider": "qweather" | "open_meteo",
  "current": {temp, feels_like, text, icon, humidity, pressure, wind_dir,
              wind_scale, wind_speed, vis, uv_index, aqi, aqi_category,
              pm25, pm10, o3},
  "daily": [{date, week, temp_max, temp_min, text_day, icon_day, wind_dir_day,
             wind_scale_day, uv_index, humidity, sunrise, sunset}],
  "fetched_at": "..."
}
缓存由 store.load/save_weather_cache 管理（默认 30 分钟）。
"""
from __future__ import annotations

import time
from datetime import datetime

import httpx

from .. import store

TIMEOUT = httpx.Timeout(20.0, connect=8.0)

WEEK_CN = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']

# WMO 天气代码 -> (中文, 图标关键字) —— Open-Meteo 使用
WMO_MAP = {
    0: ('晴', 'sunny'), 1: ('基本晴朗', 'sunny'), 2: ('多云', 'cloudy'), 3: ('阴', 'overcast'),
    45: ('雾', 'fog'), 48: ('雾凇', 'fog'),
    51: ('毛毛雨', 'drizzle'), 53: ('毛毛雨', 'drizzle'), 55: ('毛毛雨', 'drizzle'),
    61: ('小雨', 'rain'), 63: ('中雨', 'rain'), 65: ('大雨', 'rain'),
    66: ('冻雨', 'rain'), 67: ('冻雨', 'rain'),
    71: ('小雪', 'snow'), 73: ('中雪', 'snow'), 75: ('大雪', 'snow'), 77: ('雪粒', 'snow'),
    80: ('阵雨', 'rain'), 81: ('阵雨', 'rain'), 82: ('强阵雨', 'rain'),
    85: ('阵雪', 'snow'), 86: ('阵雪', 'snow'),
    95: ('雷阵雨', 'thunder'), 96: ('雷阵雨伴冰雹', 'thunder'), 99: ('雷阵雨伴冰雹', 'thunder'),
}

# 和风天气图标代码 -> 图标关键字（简化映射）
def _qweather_icon(code: str) -> str:
    try:
        c = int(code)
    except Exception:
        return 'sunny'
    if c in (100, 150):
        return 'sunny'
    if c in (101, 102, 103, 151, 152, 153):
        return 'cloudy'
    if c in (104, 154):
        return 'overcast'
    if 300 <= c < 400:
        return 'rain'
    if 400 <= c < 500:
        return 'snow'
    if 500 <= c < 600:
        return 'fog'
    return 'cloudy'


def _aqi_category(aqi) -> str:
    try:
        a = float(aqi)
    except Exception:
        return ''
    if a <= 50:
        return '优'
    if a <= 100:
        return '良'
    if a <= 150:
        return '轻度污染'
    if a <= 200:
        return '中度污染'
    if a <= 300:
        return '重度污染'
    return '严重污染'


def _wind_scale(speed_kmh) -> str:
    """风速 km/h -> 风力等级（蒲福风级近似）。"""
    try:
        s = float(speed_kmh)
    except Exception:
        return ''
    thresholds = [1, 6, 12, 20, 29, 39, 50, 62, 75, 89, 103, 118]
    for i, t in enumerate(thresholds):
        if s < t:
            return f'{i}级'
    return '12级'


def _wind_dir_cn(deg) -> str:
    try:
        d = float(deg)
    except Exception:
        return ''
    dirs = ['北风', '东北风', '东风', '东南风', '南风', '西南风', '西风', '西北风']
    return dirs[int((d + 22.5) % 360 // 45)]


def _week_of(date_str: str) -> str:
    try:
        return WEEK_CN[datetime.strptime(date_str, '%Y-%m-%d').weekday()]
    except Exception:
        return ''


# ---------------------------------------------------------------- Open-Meteo
def _fetch_open_meteo(city: dict, days: int) -> dict:
    lat, lon = city['lat'], city['lon']
    furl = ('https://api.open-meteo.com/v1/forecast'
            f'?latitude={lat}&longitude={lon}'
            '&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,'
            'pressure_msl,wind_speed_10m,wind_direction_10m,uv_index,visibility'
            '&daily=weather_code,temperature_2m_max,temperature_2m_min,uv_index_max,'
            'wind_speed_10m_max,wind_direction_10m_dominant,sunrise,sunset'
            f'&timezone=auto&forecast_days={max(1, min(days, 7))}')
    aurl = ('https://air-quality-api.open-meteo.com/v1/air-quality'
            f'?latitude={lat}&longitude={lon}&current=us_aqi,pm10,pm2_5,ozone')
    with httpx.Client(timeout=TIMEOUT) as client:
        f = client.get(furl).json()
        try:
            a = client.get(aurl).json()
        except Exception:
            a = {}
    cur = f.get('current', {})
    acur = (a.get('current') or {})
    code = cur.get('weather_code', 0)
    text, icon = WMO_MAP.get(code, ('未知', 'cloudy'))
    aqi = acur.get('us_aqi')
    current = {
        'temp': cur.get('temperature_2m'),
        'feels_like': cur.get('apparent_temperature'),
        'text': text,
        'icon': icon,
        'humidity': cur.get('relative_humidity_2m'),
        'pressure': cur.get('pressure_msl'),
        'wind_dir': _wind_dir_cn(cur.get('wind_direction_10m')),
        'wind_speed': cur.get('wind_speed_10m'),
        'wind_scale': _wind_scale(cur.get('wind_speed_10m')),
        'vis': round(cur.get('visibility', 0) / 1000, 1) if cur.get('visibility') else None,
        'uv_index': cur.get('uv_index'),
        'aqi': aqi,
        'aqi_category': _aqi_category(aqi),
        'pm25': acur.get('pm2_5'),
        'pm10': acur.get('pm10'),
        'o3': acur.get('ozone'),
    }
    d = f.get('daily', {})
    daily = []
    dates = d.get('time', [])
    for i, ds in enumerate(dates):
        dc = (d.get('weather_code') or [None] * len(dates))[i]
        dtext, dicon = WMO_MAP.get(dc, ('未知', 'cloudy'))
        ws = (d.get('wind_speed_10m_max') or [None] * len(dates))[i]
        daily.append({
            'date': ds,
            'week': _week_of(ds),
            'temp_max': (d.get('temperature_2m_max') or [None] * len(dates))[i],
            'temp_min': (d.get('temperature_2m_min') or [None] * len(dates))[i],
            'text_day': dtext,
            'icon_day': dicon,
            'wind_dir_day': _wind_dir_cn((d.get('wind_direction_10m_dominant') or [None] * len(dates))[i]),
            'wind_scale_day': _wind_scale(ws),
            'uv_index': (d.get('uv_index_max') or [None] * len(dates))[i],
            'sunrise': (d.get('sunrise') or [''] * len(dates))[i][-5:],
            'sunset': (d.get('sunset') or [''] * len(dates))[i][-5:],
        })
    return {'current': current, 'daily': daily}


# ---------------------------------------------------------------- QWeather
def _fetch_qweather(city: dict, days: int, host: str, key: str) -> dict:
    loc = f"{city['lon']},{city['lat']}"
    base = f'https://{host}'
    params = {'location': loc, 'key': key}
    with httpx.Client(timeout=TIMEOUT) as client:
        now = client.get(f'{base}/v7/weather/now', params=params).json()
        nd = '7d' if days > 3 else '3d'
        fc = client.get(f'{base}/v7/weather/{nd}', params=params).json()
        try:
            air = client.get(f'{base}/v7/air/now', params=params).json()
        except Exception:
            air = {}
    n = now.get('now', {})
    an = (air.get('now') or {})
    aqi = an.get('aqi')
    current = {
        'temp': _num(n.get('temp')),
        'feels_like': _num(n.get('feelsLike')),
        'text': n.get('text'),
        'icon': _qweather_icon(n.get('icon', '')),
        'humidity': _num(n.get('humidity')),
        'pressure': _num(n.get('pressure')),
        'wind_dir': n.get('windDir'),
        'wind_speed': _num(n.get('windSpeed')),
        'wind_scale': (n.get('windScale') or '') + '级' if n.get('windScale') else '',
        'vis': _num(n.get('vis')),
        'uv_index': None,
        'aqi': _num(aqi),
        'aqi_category': an.get('category') or _aqi_category(aqi),
        'pm25': _num(an.get('pm2p5')),
        'pm10': _num(an.get('pm10')),
        'o3': _num(an.get('o3')),
    }
    daily = []
    for d in fc.get('daily', []):
        daily.append({
            'date': d.get('fxDate'),
            'week': _week_of(d.get('fxDate', '')),
            'temp_max': _num(d.get('tempMax')),
            'temp_min': _num(d.get('tempMin')),
            'text_day': d.get('textDay'),
            'icon_day': _qweather_icon(d.get('iconDay', '')),
            'wind_dir_day': d.get('windDirDay'),
            'wind_scale_day': (d.get('windScaleDay') or '') + '级' if d.get('windScaleDay') else '',
            'uv_index': _num(d.get('uvIndex')),
            'humidity': _num(d.get('humidity')),
            'sunrise': d.get('sunrise'),
            'sunset': d.get('sunset'),
        })
    # 紫外线：和风 now 无 uv，用 daily 当天补
    if daily and current.get('uv_index') is None:
        current['uv_index'] = daily[0].get('uv_index')
    return {'current': current, 'daily': daily}


def _num(v):
    try:
        f = float(v)
        return int(f) if f == int(f) else f
    except Exception:
        return None


# ---------------------------------------------------------------- 对外入口
def _find_city(cfg: dict, city: str) -> dict:
    for c in cfg.get('cities', []):
        if c.get('name') == city or str(c.get('id')) == str(city):
            return c
    # 默认第一个
    cities = cfg.get('cities', [])
    if cities:
        return cities[0]
    raise ValueError('未配置任何城市，请先在设置中添加城市')


def get_weather(city: str, days: int = 7, use_cache: bool = True) -> dict:
    settings = store.load_settings()
    wcfg = settings.get('weather', {})
    provider = wcfg.get('provider', 'open_meteo')
    city_obj = _find_city(wcfg, city)
    cname = city_obj.get('name', city)
    today = time.strftime('%Y-%m-%d')

    if use_cache:
        cached = store.load_weather_cache(today, cname, int(wcfg.get('cache_minutes', 30)))
        if cached and cached.get('days_requested', 0) >= days:
            return cached

    if provider == 'qweather':
        host = wcfg.get('api_host') or 'devapi.qweather.com'
        key = wcfg.get('api_key')
        if not key:
            raise ValueError('和风天气未配置 API Key，请在设置中填写，或切换到 Open-Meteo')
        result = _fetch_qweather(city_obj, days, host, key)
    else:
        result = _fetch_open_meteo(city_obj, days)

    payload = {
        'city': cname,
        'provider': provider,
        'days_requested': days,
        'current': result['current'],
        'daily': result['daily'][:max(1, min(days, 7))],
        'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
    }
    try:
        store.save_weather_cache(today, cname, payload)
    except Exception:
        pass
    return payload


def search_cities(keyword: str) -> list:
    """城市搜索。和风走 GeoAPI；Open-Meteo 走 geocoding。"""
    settings = store.load_settings()
    wcfg = settings.get('weather', {})
    provider = wcfg.get('provider', 'open_meteo')
    results = []
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            if provider == 'qweather' and wcfg.get('api_key'):
                host = wcfg.get('api_host') or 'geoapi.qweather.com'
                # 和风 GeoAPI 有独立域名，优先使用官方 geoapi
                r = client.get('https://geoapi.qweather.com/v2/city/lookup',
                               params={'location': keyword, 'key': wcfg['api_key']}).json()
                for it in r.get('location', []):
                    results.append({'name': it.get('name'), 'id': it.get('id'),
                                    'lat': _num(it.get('lat')), 'lon': _num(it.get('lon')),
                                    'adm': it.get('adm')})
            else:
                r = client.get('https://geocoding-api.open-meteo.com/v1/search',
                               params={'name': keyword, 'count': 10, 'language': 'zh'}).json()
                for it in r.get('results', []):
                    results.append({'name': it.get('name'), 'id': str(it.get('id')),
                                    'lat': it.get('latitude'), 'lon': it.get('longitude'),
                                    'adm': it.get('admin1')})
    except Exception:
        pass
    return results
