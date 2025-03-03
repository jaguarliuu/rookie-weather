from collections.abc import Generator
from typing import Any
import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

GEO_API_BASE_URL = "https://restapi.amap.com/v3/geocode/geo?parameters"
WEATHER_API_BASE_URL = "https://restapi.amap.com/v3/weather/weatherInfo"

class GaodeWeatherTool(Tool):
    def _get_city_code(self, city: str) -> dict:
        """根据城市名称获取高德地图行政编码(adcode)"""
        params = {
            "address": city,
            "key": self.runtime.credentials["gaode_api_key"]
        }
        try:
            response = requests.get(GEO_API_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 检查状态码
            if data.get("status") != "1":
                self._log_error(f"高德API返回错误: {data.get('info')}")
                return {}
            
            # 处理count字段
            count = data.get("count")
            if count is None or not count.isdigit():
                self._log_error("高德API返回的count字段无效")
                return {}
            count = int(count)
            if count <= 0:
                self._log_error("高德API未找到匹配结果")
                return {}
            
            # 解析第一个匹配结果
            geocodes = data.get("geocodes", [])
            if not geocodes:
                self._log_error("高德API返回结果中无地理编码信息")
                return {}
            
            geocode = geocodes[0]
            return {"adcode": geocode.get("adcode")}
        
        except requests.exceptions.RequestException as e:
            self._log_error(f"请求高德API失败: {str(e)}")
        except Exception as e:
            self._log_error(f"解析高德API响应失败: {str(e)}")
        
        return {}
        
    def _get_weather_info(self, adcode: str, extension: str) -> dict:
        """根据高德行政编码获取天气信息"""
        params = {
            "city": adcode,
            "key": self.runtime.credentials["gaode_api_key"],
            "extensions": extension
        } 
        try:
            response = requests.get(WEATHER_API_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("status") != "1":
                self._log_error(f"Weather API Error: {data.get('info')}")
                return {}
            result = {}
            if extension == "all":
                forecasts = data.get("forecasts", [])
                if not forecasts:
                    self._log_error("Weather API预报数据缺失")
                    return {}
                # 提取城市级别的基础信息（如 province, city, reporttime 等）
                city_forecast = forecasts[0]  # 第一个 forecast 对象
                base_info = {
                    "province": city_forecast.get("province"),
                    "city": city_forecast.get("city"),
                    "adcode": city_forecast.get("adcode"),
                    "reporttime": city_forecast.get("reporttime"),
                }
                # 提取当天实时天气（casts 的第一个元素）
                today_cast = city_forecast.get("casts", [{}])[0]
                today_weather = {
                    **base_info,
                    "weather": today_cast.get("dayweather"),      # 注意：这里可能需要根据实际字段调整
                    "temperature": today_cast.get("daytemp"),
                    "winddirection": today_cast.get("daywind"),
                    "windpower": today_cast.get("daypower"),
                    "humidity": today_cast.get("humidity"),
                    "temperature_float": today_cast.get("daytemp_float"),
                    "humidity_float": today_cast.get("humidity_float"),
                }
                # 提取未来预报列表（所有 casts）
                future_forecasts = []
                for cast in city_forecast.get("casts", []):
                    future_forecasts.append({
                        "date": cast.get("date"),
                        "week": cast.get("week"),
                        "dayweather": cast.get("dayweather"),
                        "nightweather": cast.get("nightweather"),
                        "daytemp": cast.get("daytemp"),
                        "nighttemp": cast.get("nighttemp"),
                        "daywind": cast.get("daywind"),
                        "nightwind": cast.get("nightwind"),
                        "daypower": cast.get("daypower"),
                        "nightpower": cast.get("nightpower"),
                        "temperature_float": cast.get("daytemp_float"),
                        "humidity_float": cast.get("humidity_float"),
                    })
                result = {
                    **today_cast,
                    "forecasts": future_forecasts
                }
            else:
                # 处理 base 扩展：保持原有逻辑
                lives = data.get("lives", [])
                if not lives:
                    self._log_error("Weather API返回无有效数据")
                    return {}
                weather_data = lives[0]
                result = {
                    **weather_data,
                }
            return result
        except requests.exceptions.RequestException as e:
            self._log_error(f"Weather API请求失败: {str(e)}")
        except Exception as e:
            self._log_error(f"Weather API响应解析失败: {str(e)}")
        return {}
    def _log_error(self, message):
        """错误日志记录（可根据需要对接日志系统）"""
        print(f"[GaodeWeatherTool] ERROR: {message}")

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # 获取城市编码
        city_code = self._get_city_code(tool_parameters["city"])
        if not city_code:
            return {"error": "City code retrieval failed"}
        
        # 获取天气信息
        weather_info = self._get_weather_info(city_code.get("adcode"), tool_parameters["extension"])
        # 1. 通过 geo 接口获取地址的 city 
        yield self.create_json_message({
            "result": weather_info
        })
