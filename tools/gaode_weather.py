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
        
    def _get_weather_info(self, adcode: str) -> dict:
        """根据高德行政编码获取天气信息"""
        params = {
            "city": adcode,
            "key": self.runtime.credentials["gaode_api_key"]
        }
        try:
            response = requests.get(WEATHER_API_BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 结构化验证
            if data.get("status") != "1":
                self._log_error(f"Weather API Error: {data.get('info')}")
                return {}
            
            lives = data.get("lives", [])
            if not lives:
                self._log_error("Weather API返回无有效数据")
                return {}
            
            # 取第一个生活指数数据（通常对应主城区）
            weather_data = lives[0]
            
            # 提取核心字段
            result = {
                "province": weather_data.get("province"),
                "city": weather_data.get("city"),
                "adcode": weather_data.get("adcode"),
                "weather": weather_data.get("weather"),
                "temperature": weather_data.get("temperature"),
                "winddirection": weather_data.get("winddirection"),
                "windpower": weather_data.get("windpower"),
                "humidity": weather_data.get("humidity"),
                "reporttime": weather_data.get("reporttime"),
                "temperature_float": weather_data.get("temperature_float"),
                "humidity_float": weather_data.get("humidity_float")
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
        weather_info = self._get_weather_info(city_code.get("adcode"))
        # 1. 通过 geo 接口获取地址的 city 
        yield self.create_json_message({
            "result": weather_info
        })
