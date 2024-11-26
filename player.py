import json
from typing import Dict, Any, Optional
import csv
import logging
import os
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

class Player:
    """玩家类,用于管理玩家属性和状态"""
    def __init__(self, data: Dict[str, Any], player_file: str = None, standard_fields: list = None):
        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary")
        self.data = data
        self.player_file = player_file
        self.standard_fields = standard_fields
        
        # 清理耐久度为0的记录
        if 'rod_durability' in self.data:
            rod_durability = json.loads(self.data['rod_durability'])
            cleaned_durability = {rod: durability for rod, durability in rod_durability.items() if int(durability) > 0}
            self.data['rod_durability'] = json.dumps(cleaned_durability)
    @property
    def user_id(self) -> str:
        return str(self.data.get('user_id', ''))
        
    @property
    def nickname(self) -> str:
        return self.data.get('nickname', '')
        
    @property
    def gold(self) -> int:
        return int(self.data.get('gold', 0))
        
    @gold.setter 
    def gold(self, value: int):
        self.data['gold'] = str(value)
        
    @property
    def level(self) -> int:
        return int(self.data.get('level', 1))
        
    @level.setter
    def level(self, value: int):
        self.data['level'] = str(value)
        
    @property
    def hp(self) -> int:
        return int(self.data.get('hp', 100))
        
    @hp.setter
    def hp(self, value: int):
        self.data['hp'] = str(value)
        
    @property
    def max_hp(self) -> int:
        return int(self.data.get('max_hp', 100))
        
    @max_hp.setter
    def max_hp(self, value: int):
        self.data['max_hp'] = str(value)
        
    @property
    def attack(self) -> int:
        return int(self.data.get('attack', 10))
        
    @attack.setter
    def attack(self, value: int):
        self.data['attack'] = str(value)
        
    @property
    def defense(self) -> int:
        return int(self.data.get('defense', 5))
        
    @defense.setter
    def defense(self, value: int):
        self.data['defense'] = str(value)
        
    @property
    def exp(self) -> int:
        """获取经验值，确保返回整数"""
        try:
            # 先转换为浮点数，再转换为整数
            return int(float(self.data.get('exp', '0')))
        except (ValueError, TypeError):
            # 如果转换失败，返回默认值0
            return 0
        
    @exp.setter
    def exp(self, value: int):
        """设置经验值，确保存储为整数字符串"""
        try:
            # 确保value被转换为整数
            self.data['exp'] = str(int(value))
        except (ValueError, TypeError):
            # 如果转换失败，设置为0
            self.data['exp'] = '0'
        
    @property
    def inventory(self) -> list:
        return json.loads(self.data.get('inventory', '[]'))
        
    @inventory.setter
    def inventory(self, value: list):
        self.data['inventory'] = json.dumps(value)
        
    @property
    def equipped_weapon(self) -> str:
        return self.data.get('equipped_weapon', '')
        
    @equipped_weapon.setter
    def equipped_weapon(self, value: str):
        self.data['equipped_weapon'] = value
        
    @property
    def equipped_armor(self) -> str:
        return self.data.get('equipped_armor', '')
        
    @equipped_armor.setter
    def equipped_armor(self, value: str):
        self.data['equipped_armor'] = value
        
    @property
    def spouse(self) -> str:
        return self.data.get('spouse', '')
        
    @spouse.setter
    def spouse(self, value: str):
        self.data['spouse'] = value
        
    @property
    def marriage_proposal(self) -> str:
        return self.data.get('marriage_proposal', '')
        
    @marriage_proposal.setter
    def marriage_proposal(self, value: str):
        self.data['marriage_proposal'] = value
        
    @property
    def last_attack(self) -> int:
        return int(self.data.get('last_attack', 0))
        
    @last_attack.setter
    def last_attack(self, value: int):
        self.data['last_attack'] = str(value)
        
    @property
    def last_checkin(self) -> str:
        return self.data.get('last_checkin', '')
        
    @last_checkin.setter
    def last_checkin(self, value: str):
        self.data['last_checkin'] = value
        
    @property
    def last_fishing(self) -> str:
        return self.data.get('last_fishing', '')
        
    @last_fishing.setter
    def last_fishing(self, value: str):
        self.data['last_fishing'] = value
        
    @property
    def rod_durability(self) -> Dict:
        return json.loads(self.data.get('rod_durability', '{}'))
        
    @rod_durability.setter
    def rod_durability(self, value: Dict):
        self.data['rod_durability'] = json.dumps(value)
        
    @property
    def equipped_fishing_rod(self) -> str:
        return self.data.get('equipped_fishing_rod', '')
        
    @equipped_fishing_rod.setter
    def equipped_fishing_rod(self, value: str):
        self.data['equipped_fishing_rod'] = value
        
    @property
    def last_item_use(self):
        """获取上次使用物品的时间"""
        try:
            return int(self.data.get('last_item_use', '0'))
        except (ValueError, TypeError):
            # 如果转换失败，返回0作为默认值
            return 0
        
    @last_item_use.setter
    def last_item_use(self, value: int):
        """设置上次使用物品的时间"""
        self.data['last_item_use'] = str(value)

    @property
    def position(self) -> int:
        """获取玩家位置"""
        return int(self.data.get('position', '0'))
        
    @position.setter
    def position(self, value: int):
        """设置玩家位置"""
        self.data['position'] = str(value)

    def update_data(self, updates: Dict[str, Any]) -> None:
        """更新玩家数据并保存到文件"""
        if not self.player_file or not self.standard_fields:
            raise ValueError("player_file and standard_fields must be set")
            
        # 更新内存中的数据
        self.data.update(updates)
        
        # 验证数据
        if not self.validate_data():
            raise ValueError("Invalid player data after update")
            
        try:
            # 读取所有玩家数据
            players_data = []
            with open(self.player_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['user_id'] != self.user_id:
                        players_data.append(row)
            
            # 添加更新后的玩家数据
            players_data.append(self.data)
            
            # 写回文件
            with open(self.player_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.standard_fields, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(players_data)
                
        except Exception as e:
            logger.error(f"更新玩家数据出错: {e}")
            raise

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.data
        
    @classmethod
    def create_new(cls, user_id: str, nickname: str) -> 'Player':
        """创建新玩家"""
        data = {
            'user_id': user_id,
            'nickname': nickname,
            'gold': '2000',
            'level': '1', 
            'last_checkin': '',
            'inventory': '[]',
            'hp': '100',
            'max_hp': '100',
            'attack': '10',
            'defense': '5',
            'exp': '0',
            'last_fishing': '',
            'rod_durability': '{}',
            'equipped_weapon': '',
            'equipped_armor': '',
            'last_item_use': '0',
            'spouse': '',
            'marriage_proposal': '',
            'last_attack': '0',
            'position': '0'
        }
        return cls(data) 

    def get_inventory_display(self, items_info: dict) -> str:
        """获取格式化的背包显示"""
        if not self.inventory:
            return "背包是空的"
            
        # 统计物品数量
        from collections import Counter
        item_counts = Counter(self.inventory)
        
        # 按类型分类物品
        weapons = []
        armors = []
        consumables = []
        fish = []
        fishing_rods = []
        others = []
        
        for item_name, count in item_counts.items():
            item_info = items_info.get(item_name, {})
            stats = []
            
            # 获取物品属性
            if item_info.get('hp', '0') != '0':
                stats.append(f"生命值增加{item_info['hp']}")
            if item_info.get('attack', '0') != '0':
                stats.append(f"攻击力增加{item_info['attack']}")
            if item_info.get('defense', '0') != '0':
                stats.append(f"防御力增加{item_info['defense']}")
            
            stats_str = f"({', '.join(stats)})" if stats else ""
            equipped_str = ""
            
            if item_name == self.equipped_weapon:
                equipped_str = "⚔️已装备"
            elif item_name == self.equipped_armor:
                equipped_str = "🛡️已装备"
            elif item_name == self.equipped_fishing_rod:
                equipped_str = "🎣已装备"
                
            durability_str = ""
            if item_info.get('type') == 'fishing_rod':
                durability = self.rod_durability.get(item_name, 100)
                durability_str = f" [耐久度:{durability}%]"
                
            item_str = f"{item_name} x{count} {equipped_str} {stats_str}{durability_str}"
            
            # 根据物品类型分类
            item_type = item_info.get('type', '')
            if item_type == 'weapon':
                weapons.append(item_str)
            elif item_type == 'armor':
                armors.append(item_str)
            elif item_type == 'consumable':
                consumables.append(item_str)
            elif item_type == 'fishing_rod':
                fishing_rods.append(item_str)
            elif item_type == 'fish':
                fish.append(item_str)
            else:
                others.append(item_str)
        
        # 生成背包显示
        inventory_list = ["🎒 背包物品\n"]
        
        if weapons:
            inventory_list.append("⚔️ 武器:")
            inventory_list.extend(f"  {w}" for w in weapons)
            inventory_list.append("")
            
        if armors:
            inventory_list.append("🛡️ 防具:")
            inventory_list.extend(f"  {a}" for a in armors)
            inventory_list.append("")
            
        if fishing_rods:
            inventory_list.append("🎣 鱼竿:")
            inventory_list.extend(f"  {r}" for r in fishing_rods)
            inventory_list.append("")
            
        if consumables:
            inventory_list.append("🎁 消耗品:")
            inventory_list.extend(f"  {c}" for c in consumables)
            inventory_list.append("")
            
        if fish:
            inventory_list.append("🐟 鱼类:")
            inventory_list.extend(f"  {f}" for f in fish)
            inventory_list.append("")
            
        if others:
            inventory_list.append("📦 其他物品:")
            inventory_list.extend(f"  {o}" for o in others)
        
        return "\n".join(inventory_list).strip()

    def has_item(self, item_name: str) -> bool:
        """检查是否拥有指定物品"""
        return item_name in self.inventory

    @classmethod
    def get_player(cls, user_id: str, player_file: str) -> Optional['Player']:
        """从文件中获取玩家数据
        
        Args:
            user_id: 用户ID
            player_file: 玩家数据文件路径
            
        Returns:
            Optional[Player]: 玩家实例,如果未找到则返回 None
        """
        try:
            with open(player_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['user_id'] == str(user_id):
                        logger.info(f"找到用户ID为 {user_id} 的玩家数据")
                        return cls(row)
            logger.warning(f"未找到用户ID为 {user_id} 的玩家数据")
            return None
        except FileNotFoundError:
            logger.error(f"玩家数据文件 {player_file} 未找到")
            return None
        except Exception as e:
            logger.error(f"获取玩家数据出错: {e}")
            return None

    def save_player_data(self, player_file: str, standard_fields: list) -> None:
        """保存玩家数据到CSV文件
        
        Args:
            player_file: 玩家数据文件路径
            standard_fields: 标准字段列表
        """
        try:
            # 读取所有玩家数据
            players_data = []
            with open(player_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['user_id'] != self.user_id:
                        players_data.append(row)
            
            # 添加更新后的玩家数据
            players_data.append(self.to_dict())
            
            # 写回文件
            with open(player_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=standard_fields, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(players_data)
                
        except Exception as e:
            logger.error(f"保存玩家数据出错: {e}")
            raise

    def validate_data(self) -> bool:
        """验证玩家数据的完整性"""
        required_fields = {
            'user_id': str,
            'nickname': str,
            'gold': (str, int),
            'level': (str, int),
            'hp': (str, int),
            'max_hp': (str, int),
            'attack': (str, int),
            'defense': (str, int),
            'exp': (str, int),
            'position': (str, int)
        }
        
        try:
            for field, types in required_fields.items():
                if field not in self.data:
                    logger.error(f"Missing required field: {field}")
                    return False
                
                value = self.data[field]
                if isinstance(types, tuple):
                    if not isinstance(value, types):
                        try:
                            # 尝试转换为字符串
                            self.data[field] = str(value)
                        except:
                            logger.error(f"Invalid type for field {field}: {type(value)}")
                            return False
                else:
                    if not isinstance(value, types):
                        logger.error(f"Invalid type for field {field}: {type(value)}")
                        return False
            return True
        except Exception as e:
            logger.error(f"Data validation error: {e}")
            return False

    def _backup_data(self):
        """创建数据文件的备份"""
        if not self.player_file:
            return
            
        backup_dir = os.path.join(os.path.dirname(self.player_file), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'players_{timestamp}.csv')
        
        try:
            shutil.copy2(self.player_file, backup_file)
        except Exception as e:
            logger.error(f"创建数据备份失败: {e}")

    def get_player_status(self, items_info: dict) -> str:
        """获取家状态并检查异常
        
        Args:
            items_info: 物品信息字典
            
        Returns:
            str: 格式化的玩家状态信息
        """
        # 计算正常情况下应有的属性值
        current_level = self.level
        level_bonus_hp = (current_level - 1) * 50  # 每级增加50血量
        level_bonus_attack = (current_level - 1) * 15  # 每级增加15攻击
        level_bonus_defense = (current_level - 1) * 10  # 每级增加10防御
        
        expected_max_hp = 100 + level_bonus_hp  # 基础100血量
        expected_base_attack = 10 + level_bonus_attack  # 基础10攻击
        expected_base_defense = 5 + level_bonus_defense  # 基础5防御
        
        # 检查并纠正异常属性
        needs_update = False
        updates = {}
        
        if self.max_hp != expected_max_hp:
            updates['max_hp'] = str(expected_max_hp)
            needs_update = True
            
        if self.attack != expected_base_attack:
            updates['attack'] = str(expected_base_attack)
            needs_update = True
            
        if self.defense != expected_base_defense:
            updates['defense'] = str(expected_base_defense)
            needs_update = True
        
        # 如果生命值超过最大生命值，进行修正
        if int(self.hp) > expected_max_hp:
            updates['hp'] = str(expected_max_hp)
            needs_update = True
            
        # 如果发现异常，更新数据
        if needs_update:
            self.update_data(updates)
        
        # 获取装备加成
        equipped_weapon = self.equipped_weapon
        equipped_armor = self.equipped_armor
        equipped_fishing_rod = self.equipped_fishing_rod
        
        # 基础属性(使用可能已经修正的值)
        base_attack = self.attack
        base_defense = self.defense
        
        # 装备加成
        weapon_bonus = 0
        armor_bonus = 0
        
        # 获取武器加成
        if equipped_weapon and equipped_weapon in items_info:
            weapon_info = items_info[equipped_weapon]
            weapon_bonus = int(weapon_info.get('attack', 0))
            weapon_stats = []
            if weapon_info.get('attack', '0') != '0':
                weapon_stats.append(f"攻击{weapon_info['attack']}")
            if weapon_info.get('defense', '0') != '0':
                weapon_stats.append(f"防御{weapon_info['defense']}")
            weapon_str = f"{equipped_weapon}({', '.join(weapon_stats)})" if weapon_stats else equipped_weapon
        else:
            weapon_str = "无"

        # 获取护甲加成
        if equipped_armor and equipped_armor in items_info:
            armor_info = items_info[equipped_armor]
            armor_bonus = int(armor_info.get('defense', 0))
            hp_bonus = int(armor_info.get('hp', 0))  # 添加生命值加成
            armor_stats = []
            if armor_info.get('attack', '0') != '0':
                armor_stats.append(f"攻击{armor_info['attack']}")
            if armor_info.get('defense', '0') != '0':
                armor_stats.append(f"防御{armor_info['defense']}")
            if armor_info.get('hp', '0') != '0':  # 添加生命值显示
                armor_stats.append(f"生命{armor_info['hp']}")
            armor_str = f"{equipped_armor}({', '.join(armor_stats)})" if armor_stats else equipped_armor
        else:
            armor_str = "无"
            armor_bonus = 0
            hp_bonus = 0  # 无装备时生命值加成为0
        
        # 计算总属性
        total_attack = base_attack + weapon_bonus
        total_defense = base_defense + armor_bonus
        total_max_hp = self.max_hp + hp_bonus  # 计算总生命值上限
        
        # 婚姻状态
        spouses = self.spouse.split(',') if self.spouse else []
        spouses = [s for s in spouses if s]  # 过滤空字符串
        
        if spouses:
            marriage_status = f"已婚 (配偶: {', '.join(spouses)})"
        else:
            marriage_status = "单身"
            
        if self.marriage_proposal:
            # 获取求婚者的昵称
            proposer = self.get_player(self.marriage_proposal, self.player_file)
            if proposer:
                proposer_name = proposer.nickname
            else:
                proposer_name = f"@{self.marriage_proposal}"
            marriage_status += f"\n💝 收到来自 {proposer_name} 的求婚"
        
        # 构建状态信息
        status = [
            f"🏷️ 玩家: {self.nickname}",
            f"💰 金币: {self.gold}",
            f"📊 等级: {current_level}",
            f"✨ 经验: {self.exp}/{int(current_level * 100 * (1 + (current_level - 1) * 0.5))}",
            f"❤️ 生命值: {self.hp}/{total_max_hp} (基础{self.max_hp} / 装备{hp_bonus})",  # 修改生命值显示
            f"⚔️ 攻击力: {total_attack} (基础{base_attack} / 装备{weapon_bonus})",
            f"🛡️ 防御力: {total_defense} (基础{base_defense} / 装备{armor_bonus})",
            f"🗡️ 装备武器: {weapon_str}",
            f"🛡️ 装备护甲: {armor_str}",
            f"💕 婚姻状态: {marriage_status}"
        ]
        
        if needs_update:
            status.insert(1, "⚠️ 检测到属性异常已自动修正")
        
        # 如果装备了鱼竿，显示鱼竿信息
        if equipped_fishing_rod:
            rod_durability = self.rod_durability.get(equipped_fishing_rod, 100)
            status.append(f"🎣 装备鱼竿: {equipped_fishing_rod} [耐久度:{rod_durability}%]")
        
        return "\n".join(status)

    @classmethod
    def get_player_by_nickname(cls, nickname: str, player_file: str) -> Optional['Player']:
        """根据昵称查找玩家
        
        Args:
            nickname: 玩家昵称
            player_file: 玩家数据文件路径
            
        Returns:
            Optional[Player]: 玩家实例,如果未找到则返回 None
        """
        try:
            with open(player_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['nickname'] == nickname:
                        logger.info(f"找到昵称为 {nickname} 的玩家数据")
                        return cls(row)
            logger.warning(f"未找到昵称为 {nickname} 的玩家数据")
            return None
        except FileNotFoundError:
            logger.error(f"玩家数据文件 {player_file} 未找到")
            return None
        except Exception as e:
            logger.error(f"根据昵称获取玩家数据出错: {e}")
            return None
