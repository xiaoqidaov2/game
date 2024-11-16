import json
import random
import os
from typing import Dict, List, Optional

class MonopolySystem:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.map_file = os.path.join(data_dir, "map_config.json")
        self.events_file = os.path.join(data_dir, "events_config.json")
        self.properties_file = os.path.join(data_dir, "properties.json")
        
        # 初始化地图和事件数据
        self._init_map_config()
        self._init_events_config()
        self._init_properties()
        
        # 加载数据
        self.map_data = self._load_json(self.map_file)
        self.events_data = self._load_json(self.events_file)
        self.properties_data = self._load_json(self.properties_file)
        
    def _init_map_config(self):
        """初始化地图配置"""
        if not os.path.exists(self.map_file):
            default_map = {
                "total_blocks": 50,
                "blocks": {
                    "0": {"type": "起点", "name": "首都北京", "description": "每次经过可获得200金币", "region": "直辖市"},
                    "12": {"type": "直辖市", "name": "上海", "description": "繁华的国际大都市", "region": "直辖市"},
                    "25": {"type": "直辖市", "name": "重庆", "description": "山城魅力", "region": "直辖市"},
                    "37": {"type": "直辖市", "name": "天津", "description": "北方港口城市", "region": "直辖市"},
                    
                    "5": {"type": "省会", "name": "广州", "description": "广东省会", "region": "省会"},
                    "17": {"type": "省会", "name": "成都", "description": "四川省会", "region": "省会"},
                    "30": {"type": "省会", "name": "杭州", "description": "浙江省会", "region": "省会"},
                    "42": {"type": "省会", "name": "南京", "description": "江苏省会", "region": "省会"},
                    "6": {"type": "省会", "name": "武汉", "description": "湖北省会", "region": "省会"},
                    "18": {"type": "省会", "name": "长沙", "description": "湖南省会", "region": "省会"},
                    "31": {"type": "省会", "name": "西安", "description": "陕西省会", "region": "省会"},
                    "43": {"type": "省会", "name": "郑州", "description": "河南省会", "region": "省会"},
                    
                    "7": {"type": "地级市", "name": "苏州", "description": "江苏重要城市", "region": "地级市"},
                    "20": {"type": "地级市", "name": "青岛", "description": "山东重要城市", "region": "地级市"},
                    "32": {"type": "地级市", "name": "厦门", "description": "福建重要城市", "region": "地级市"},
                    "45": {"type": "地级市", "name": "大连", "description": "辽宁重要城市", "region": "地级市"},
                    "8": {"type": "地级市", "name": "宁波", "description": "浙江重要城市", "region": "地级市"},
                    "21": {"type": "地级市", "name": "无锡", "description": "江苏重要城市", "region": "地级市"},
                    "33": {"type": "地级市", "name": "珠海", "description": "广东重要城市", "region": "地级市"},
                    "46": {"type": "地级市", "name": "深圳", "description": "广东重要城市", "region": "地级市"},
                    
                    "2": {"type": "县城", "name": "周庄古镇", "description": "江南水乡", "region": "县城"},
                    "15": {"type": "县城", "name": "凤凰古城", "description": "湘西名城", "region": "县城"},
                    "27": {"type": "县城", "name": "婺源县", "description": "徽派建筑", "region": "县城"},
                    "40": {"type": "县城", "name": "丽江古城", "description": "云南名城", "region": "县城"},
                    "3": {"type": "县城", "name": "乌镇", "description": "浙江古镇", "region": "县城"},
                    "16": {"type": "县城", "name": "平遥古城", "description": "山西古城", "region": "县城"},
                    "28": {"type": "县城", "name": "西塘古镇", "description": "江南古镇", "region": "县城"},
                    "41": {"type": "县城", "name": "阳朔县", "description": "桂林山水", "region": "县城"},
                    
                    "10": {"type": "乡村", "name": "婺源篁岭", "description": "徽州晒秋", "region": "乡村"},
                    "22": {"type": "乡村", "name": "阿坝草原", "description": "四川草原", "region": "乡村"},
                    "35": {"type": "乡村", "name": "婺源晓起", "description": "徽州村落", "region": "乡村"},
                    "47": {"type": "乡村", "name": "云南梯田", "description": "哈尼梯田", "region": "乡村"},
                    "11": {"type": "乡村", "name": "江西武功山", "description": "高山草甸", "region": "乡村"},
                    "23": {"type": "乡村", "name": "新疆喀纳斯", "description": "图瓦人村落", "region": "乡村"},
                    "36": {"type": "乡村", "name": "福建土楼", "description": "客家文化", "region": "乡村"},
                    "48": {"type": "乡村", "name": "西双版纳", "description": "傣族村寨", "region": "乡村"},

                    "9": {"type": "机遇", "name": "机遇空间", "description": "触发随机事件", "region": "机遇"},
                    "19": {"type": "机遇", "name": "命运转盘", "description": "触发随机事件", "region": "机遇"},
                    "34": {"type": "机遇", "name": "幸运空间", "description": "触发随机事件", "region": "机遇"},
                    "44": {"type": "机遇", "name": "命运空间", "description": "触发随机事件", "region": "机遇"}
                },
                "default_block": {"type": "森林", "name": "神秘森林", "description": "危险的森林,可能遇到怪物", "region": "森林"}
            }
            self._save_json(self.map_file, default_map)

    def _init_events_config(self):
        """初始化事件配置"""
        if not os.path.exists(self.events_file):
            default_events = {
                "good_events": [
                    {
                        "id": "treasure",
                        "name": "发现宝藏",
                        "description": "你发现了一个古老的宝箱",
                        "effect": {"gold": 500}
                    },
                    {
                        "id": "lottery",
                        "name": "中奖啦",
                        "description": "你买的彩票中奖了",
                        "effect": {"gold": 300}
                    }
                ],
                "bad_events": [
                    {
                        "id": "tax",
                        "name": "缴税",
                        "description": "需要缴纳一些税款",
                        "effect": {"gold": -200}
                    },
                    {
                        "id": "robbery",
                        "name": "被偷窃",
                        "description": "你的钱包被偷了",
                        "effect": {"gold": -100}
                    }
                ]
            }
            self._save_json(self.events_file, default_events)

    def _init_properties(self):
        """初始化地产数据"""
        if not os.path.exists(self.properties_file):
            self._save_json(self.properties_file, {})

    def _load_json(self, file_path: str) -> dict:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载{file_path}失败: {e}")
            return {}

    def _save_json(self, file_path: str, data: dict):
        """保存JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存{file_path}失败: {e}")

    def roll_dice(self) -> int:
        """掷骰子"""
        return random.randint(1, 6)

    def get_block_info(self, position: int) -> dict:
        """获取指定位置的地块信息"""
        position = position % self.map_data["total_blocks"]
        return self.map_data["blocks"].get(str(position), self.map_data["default_block"])

    def get_property_owner(self, position: int) -> Optional[str]:
        """获取地块所有者"""
        return self.properties_data.get(str(position))

    def buy_property(self, position: int, player_id: str, price: int) -> bool:
        """购买地块"""
        if str(position) in self.properties_data:
            return False
        
        self.properties_data[str(position)] = {
            "owner": player_id,
            "level": 1,
            "price": price
        }
        self._save_json(self.properties_file, self.properties_data)
        return True

    def calculate_property_price(self, position: int) -> int:
        """计算地块价格"""
        block = self.get_block_info(position)
        base_price = 500
        
        # 根据地区类型设置基础价格
        region_multipliers = {
            "直辖市": 5.0,
            "省会": 3.0,
            "地级市": 2.0,
            "县城": 1.5,
            "乡村": 1.0,
            "其他": 1.0
        }
        
        # 根据距离起点的远近调整价格
        distance_factor = 1 + (position % 10) * 0.1
        
        # 计算最终价格
        final_price = int(base_price * region_multipliers[block["region"]] * distance_factor)
        return final_price

    def calculate_rent(self, position: int) -> int:
        """计算租金"""
        property_data = self.properties_data.get(str(position))
        if not property_data:
            return 0
        
        block = self.get_block_info(position)
        base_rent = property_data["price"] * 0.1
        
        # 根据地区类型设置租金倍率
        region_multipliers = {
            "直辖市": 2.0,
            "省会": 1.5,
            "地级市": 1.3,
            "县城": 1.2,
            "乡村": 1.0,
            "其他": 1.0
        }
        
        # 根据地产等级增加租金
        level_multiplier = property_data["level"] * 0.5
        
        # 计算最终租金
        final_rent = int(base_rent * region_multipliers[block["region"]] * (1 + level_multiplier))
        return final_rent

    def get_property_info(self, position: int) -> dict:
        """获取地产详细信息"""
        property_data = self.properties_data.get(str(position))
        if not property_data:
            return None
        
        block = self.get_block_info(position)
        return {
            "name": block["name"],
            "type": block["type"],
            "region": block["region"],
            "level": property_data["level"],
            "price": property_data["price"],
            "rent": self.calculate_rent(position),
            "owner": property_data["owner"]
        }

    def trigger_random_event(self) -> dict:
        """触发随机事件"""
        event_type = random.choice(["good_events", "bad_events"])
        events = self.events_data[event_type]
        return random.choice(events)

    def upgrade_property(self, position: int) -> bool:
        """升级地产"""
        if str(position) not in self.properties_data:
            return False
            
        property_data = self.properties_data[str(position)]
        if property_data["level"] >= 3:  # 最高3级
            return False
            
        property_data["level"] += 1
        self._save_json(self.properties_file, self.properties_data)
        return True

    def get_player_properties(self, player_id: str) -> List[int]:
        """获取玩家的所有地产"""
        return [
            int(pos) for pos, data in self.properties_data.items()
            if data["owner"] == player_id
        ] 
