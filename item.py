import csv
import json
from typing import Dict, Any, Optional
from common.log import logger
import os

class Item:
    """物品类,用于管理物品属性和操作"""
    
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.item_file = f"{data_dir}/items.csv"
        
    def get_all_items(self) -> Dict[str, Dict[str, Any]]:
        """获取所有物品信息"""
        items_info = {}
        try:
            # 读取物品数据
            with open(self.item_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    items_info[row['name']] = row
            return items_info
        except Exception as e:
            logger.error(f"读取物品数据出错: {e}")
            return {}
            
    def init_default_items(self):
        """初始化默认物品数据"""
        if not os.path.exists(self.item_file):
            with open(self.item_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 添加价格和稀有度字段
                writer.writerow(['name', 'desc', 'type', 'hp', 'attack', 'defense', 'price', 'rarity'])
                # 写入默认装备数据
                default_items = [
                    ['木剑', '一把普通的木剑', 'weapon', '0', '5', '0', '100', '1'],
                    ['铁剑', '更坚固的铁剑', 'weapon', '0', '10', '0', '300', '2'],
                    ['精钢剑', '由精钢打造的利剑', 'weapon', '0', '20', '0', '600', '3'],
                    ['符文剑', '刻有魔法符文的剑', 'weapon', '0', '35', '0', '1000', '4'],
                    ['龙骨剑', '以龙骨制成的神剑', 'weapon', '0', '50', '0', '2000', '5'],
                    ['混沌之刃', '蕴含混沌之力的魔剑', 'weapon', '0', '75', '0', '4000', '6'],
                    ['毁灭之剑', '传说中的毁灭神器', 'weapon', '0', '100', '0', '8000', '7'],
                    ['布甲', '简单的布制护甲', 'armor', '20', '0', '5', '150', '1'],
                    ['铁甲', '结实的铁制护甲', 'armor', '50', '0', '15', '400', '2'],
                    ['精钢甲', '精钢打造的铠甲', 'armor', '100', '0', '30', '800', '3'],
                    ['符文甲', '刻有防护符文的铠甲', 'armor', '150', '0', '45', '1500', '4'],
                    ['龙鳞甲', '龙鳞制成的铠甲', 'armor', '200', '0', '60', '3000', '5'],
                    ['神圣铠甲', '具有神圣力量的铠甲', 'armor', '250', '0', '75', '6000', '6'],
                    ['永恒战甲', '传说中的不朽铠甲', 'armor', '300', '0', '90', '10000', '7'],
                    ['面包', '回复20点生命值', 'consumable', '20', '0', '0', '20', '1'],
                    ['药水', '回复50点生命值', 'consumable', '50', '0', '0', '50', '1'],
                    ['道生羽的节操', '毫无作用的道具(笑)', 'consumable', '0', '0', '0', '1', '1'],
                    ['木制鱼竿', '简单的木制鱼竿', 'fishing_rod', '0', '1', '0', '200', '1'],
                    ['铁制鱼竿', '更好的铁制鱼竿', 'fishing_rod', '0', '2', '0', '500', '2'],
                    ['金制鱼竿', '稀有的金制鱼竿', 'fishing_rod', '0', '3', '0', '1000', '3']
                ]
                writer.writerows(default_items)
                
                # 写入鱼类数据
                fish_data = [
                    ['小鱼', '一条小鱼', 'fish', '0', '0', '0', '12', '1'],
                    ['鲫鱼', '普通的鲫鱼', 'fish', '0', '0', '0', '24', '2'],
                    # ... 其他鱼类数据 ...
                ]
                writer.writerows(fish_data)
            
    def get_shop_items(self) -> Dict[str, Dict[str, Any]]:
        """获取商店物品信息"""
        items = {}
        try:
            # 读取物品数据
            with open(self.item_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 只返回非鱼类物品
                    if row.get('type') != 'fish':
                        items[row['name']] = row
            return items
        except Exception as e:
            logger.error(f"读取商店物品数据出错: {e}")
            return {}