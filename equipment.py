import json
from typing import Dict, Any, Optional
from common.log import logger

class Equipment:
    """装备系统类,用于管理装备相关功能"""
    
    def __init__(self, game):
        self.game = game
        
    def equip_item(self, user_id: str, item_name: str) -> str:
        """装备物品"""
        player = self.game.get_player(user_id)
        if not player:
            return "您还没注册..."
            
        # 获取物品信息
        items = self.game.item_system.get_all_items()
        if item_name not in items:
            return "没有这个物品"
            
        item = items[item_name]
        item_type = item.get('type')
        
        # 检查是否是装备类型
        if item_type not in ['weapon', 'armor']:
            return "该物品不能装备"
            
        # 检查玩家是否拥有该物品
        if not player.has_item(item_name):
            return "您没有这个物品"
            
        # 获取装备前的属性
        old_stats = self.get_equipment_stats(user_id)
        
        # 获取当前装备和背包
        current_slot = 'equipped_weapon' if item_type == 'weapon' else 'equipped_armor'
        current_equipment = getattr(player, current_slot)
        inventory = player.inventory
        
        # 更新数据
        updates = {current_slot: item_name}
        
        # 如果有已装备的物品,放回背包
        if current_equipment:
            inventory.append(current_equipment)
            
        # 从背包中移除新装备
        inventory.remove(item_name)
        updates['inventory'] = inventory
        
        # 更新玩家数据
        self.game._update_player_data(user_id, updates)
        
        # 获取装备后的属性
        new_stats = self.get_equipment_stats(user_id)
        
        # 计算属性变化
        attack_change = new_stats['attack'] - old_stats['attack']
        defense_change = new_stats['defense'] - old_stats['defense']
        hp_change = new_stats['hp'] - old_stats['hp']
        
        # 构建属性变化提示
        changes = []
        if attack_change != 0:
            changes.append(f"攻击力{'+' if attack_change > 0 else ''}{attack_change}")
        if defense_change != 0:
            changes.append(f"防御力{'+' if defense_change > 0 else ''}{defense_change}")
        if hp_change != 0:
            changes.append(f"生命值{'+' if hp_change > 0 else ''}{hp_change}")
            
        equip_type = "武器" if item_type == 'weapon' else "护甲"
        change_str = f"({', '.join(changes)})" if changes else ""
        
        # 如果有已装备的物品,显示替换信息
        if current_equipment:
            return f"成功将{equip_type}从 {current_equipment} 替换为 {item_name} {change_str}"
        else:
            return f"成功装备{equip_type} {item_name} {change_str}"
        
    def unequip_item(self, user_id: str, item_type: str) -> str:
        """卸下装备"""
        player = self.game.get_player(user_id)
        if not player:
            return "您还没注册..."
            
        # 检查装备类型
        if item_type not in ['weapon', 'armor']:
            return "无效的装备类型"
            
        # 获取当前装备
        slot = 'equipped_weapon' if item_type == 'weapon' else 'equipped_armor'
        current_equipment = getattr(player, slot)
        
        if not current_equipment:
            return f"没有装备{item_type}"
            
        # 更新背包
        inventory = player.inventory  # 已经是 list 类型
        inventory.append(current_equipment)
        
        # 更新数据
        updates = {
            slot: '',
            'inventory': inventory  # Player 类会自动处理 JSON 转换
        }
        self.game._update_player_data(user_id, updates)
        
        equip_type = "武器" if item_type == 'weapon' else "护甲"
        return f"成功卸下{equip_type} {current_equipment}"
        
    def get_equipment_stats(self, user_id: str) -> Dict[str, int]:
        """获取玩家装备属性加成"""
        player = self.game.get_player(user_id)
        if not player:
            return {'attack': 0, 'defense': 0, 'hp': 0}
            
        items = self.game.item_system.get_all_items()
        stats = {'attack': 0, 'defense': 0, 'hp': 0}
        
        # 计算武器加成
        weapon = getattr(player, 'equipped_weapon', '')
        if weapon and weapon in items:
            weapon_item = items[weapon]
            stats['attack'] += int(weapon_item.get('attack', 0))
            stats['defense'] += int(weapon_item.get('defense', 0))
            stats['hp'] += int(weapon_item.get('hp', 0))
            
        # 计算护甲加成
        armor = getattr(player, 'equipped_armor', '')
        if armor and armor in items:
            armor_item = items[armor]
            stats['attack'] += int(armor_item.get('attack', 0))
            stats['defense'] += int(armor_item.get('defense', 0))
            stats['hp'] += int(armor_item.get('hp', 0))
            
        return stats

    def get_weapon_bonus(self, player) -> int:
        """获取武器攻击加成"""
        if not player.equipped_weapon:
            return 0
        
        items = self.game.item_system.get_all_items()
        weapon = items.get(player.equipped_weapon)
        if not weapon:
            return 0
        
        return int(weapon.get('attack', 0))

    def get_armor_reduction(self, target) -> float:
        """获取护甲减伤比例"""
        if isinstance(target, dict):  # 如果是怪物
            return 0.0  # 怪物没有装备,返回0减伤
        
        if not target.equipped_armor:
            return 0.0
        
        items = self.game.item_system.get_all_items()
        armor = items.get(target.equipped_armor)
        if not armor:
            return 0.0
        
        # 将防御值转换为减伤比例,每点防御提供1%减伤,最高80%
        reduction = min(0.8, int(armor.get('defense', 0)) * 0.01)
        return reduction
