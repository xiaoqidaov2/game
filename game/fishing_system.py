import csv
import random
import json
import datetime
import os
from common.log import logger

class FishingSystem:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.item_file = os.path.join(data_dir, "items.csv")
        
    def go_fishing(self, player, rod):
        """钓鱼主逻辑"""
        # 根据鱼竿类型设置基础属性
        rod_attributes = {
            '木制鱼竿': {
                'base_chance': 0.6,
                'durability_bonus': 1.0,
                'cooldown_reduction': 1.0
            },
            '铁制鱼竿': {
                'base_chance': 0.75,
                'durability_bonus': 1.2,
                'cooldown_reduction': 0.8
            },
            '金制鱼竿': {
                'base_chance': 0.9,
                'durability_bonus': 1.5,
                'cooldown_reduction': 0.6
            }
        }[rod]
        
        base_chance = rod_attributes['base_chance']
        durability_bonus = rod_attributes['durability_bonus']
        
        # 获取当前耐久度
        rod_durability = player.rod_durability
        if rod not in rod_durability:
            rod_durability[rod] = 100
        current_durability = rod_durability[rod]
        
        # 随机判断是否钓到鱼
        if random.random() < base_chance:
            # 读取鱼的数据
            fish_data = []
            with open(self.item_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['type'] == 'fish':  # 只获取鱼类物品
                        fish_data.append(row)
                
            # 根据稀有度加权随机选择一条鱼
            weights = [1/int(row.get('rarity', '1')) for row in fish_data]
            total_weight = sum(weights)
            normalized_weights = [w/total_weight for w in weights]
            
            caught_fish = random.choices(fish_data, normalized_weights)[0]
            
            # 修改耐久度消耗计算
            base_durability_cost = random.randint(5, 15)
            durability_cost = max(1, int(base_durability_cost / durability_bonus))
            
            # 修改金币奖励计算逻辑
            base_reward = int(caught_fish.get('price', '0')) * 0.3
            rod_bonus = {
                '木制鱼竿': 1.0,
                '铁制鱼竿': 1.2,
                '金制鱼竿': 1.5
            }[rod]
            
            coins_reward = max(1, int(base_reward * rod_bonus))
            
            # 生成钓鱼信息
            fishing_messages = [
                "🎯 哇！鱼儿上钩了！",
                "🎣 成功钓到一条鱼！",
                "🌊 收获颇丰！",
                "✨ 技术不错！",
                "🎪 今天运气不错！"
            ]
            
            # 计算耐久度百分比
            remaining_durability = current_durability - durability_cost
            
            stars = "⭐" * int(caught_fish.get('rarity', '1'))
            message = f"{random.choice(fishing_messages)}\n"
            message += f"━━━━━━━━━━━━━━━\n"
            message += f"🎣 你钓到了 {caught_fish['name']}\n"
            message += f"📊 稀有度: {stars}\n"
            message += f"💰 基础价值: {caught_fish.get('price', '0')}金币\n"
            message += f"🎯 鱼竿加成: x{rod_bonus} ({rod})\n"
            message += f"🪙 实际获得: {coins_reward}金币\n"
            message += f"⚡ 耐久消耗: -{durability_cost} ({remaining_durability}/100)\n"
            message += f"🎲 当前幸运值: {base_chance*100:.0f}%\n"
            message += f"━━━━━━━━━━━━━━━"
            
            return {
                'success': True,
                'fish': caught_fish,
                'durability_cost': durability_cost,
                'coins_reward': coins_reward,
                'message': message
            }
        else:
            # 未钓到鱼时的处理逻辑保持不变
            fail_messages = [
                "🌊 鱼儿溜走了...",
                "💨 这次什么都没钓到",
                "❌ 差一点就抓到了",
                "💪 继续努力！",
                "🎣 下次一定能钓到！"
            ]
            base_durability_cost = random.randint(1, 5)
            durability_cost = max(1, int(base_durability_cost / durability_bonus))
            remaining_durability = current_durability - durability_cost
            
            message = f"{random.choice(fail_messages)}\n"
            message += f"━━━━━━━━━━━━━━━\n"
            message += f"⚡ 耐久消耗: -{durability_cost} ({remaining_durability}/100)\n"
            message += f"🎲 当前幸运值: {base_chance*100:.0f}%\n"
            message += f"━━━━━━━━━━━━━━━"
            
            return {
                'success': False,
                'durability_cost': durability_cost,
                'message': message
            }

    def show_collection(self, player, page=1, search_term=""):
        """显示鱼类图鉴"""
        # 读取玩家背包
        inventory = player.inventory
        
        # 统计鱼的数量
        from collections import Counter
        fish_counts = Counter(inventory)
        
        # 读取所有鱼类信息
        fish_data = {}
        with open(self.item_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['type'] == 'fish':  # 只获取鱼类物品
                    fish_data[row['name']] = {
                        'rarity': int(row['rarity']),
                        'price': int(row['price'])
                    }
        
        # 按稀有度排序
        sorted_fish = sorted(fish_data.items(), key=lambda x: (-x[1]['rarity'], x[0]))
        
        # 搜索过滤
        if search_term:
            sorted_fish = [(name, data) for name, data in sorted_fish if search_term in name]
            if not sorted_fish:
                return f"未找到包含 '{search_term}' 的鱼类"
        
        # 分页处理
        items_per_page = 20
        total_pages = (len(sorted_fish) + items_per_page - 1) // items_per_page
        
        if page < 1 or page > total_pages:
            page = 1
            
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_fish = sorted_fish[start_idx:end_idx]
        
        # 生成图鉴信息
        collection = f"📖 鱼类图鉴 (第{page}/{total_pages}页)\n"
        collection += "══════════════════\n\n"
        
        for fish_name, data in page_fish:
            count = fish_counts.get(fish_name, 0)
            stars = "⭐" * data['rarity']
            collection += f"🐟 {fish_name}\n"
            collection += f"   收集数量: {count}\n"
            collection += f"   稀有度: {stars}\n"
            collection += f"   价值: 💰{data['price']}金币\n"
            collection += "──────────────\n"
            
        collection += "\n💡 使用方法:\n"
        collection += "• 图鉴 [页码] - 查看指定页\n"
        collection += "• 图鉴 [鱼名] - 搜索特定鱼类"
        
        return collection
