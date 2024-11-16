import os
import csv
import random
from plugins import *
from common.log import logger
from bridge.context import ContextType, Context
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
import plugins
import time
from typing import Optional
from .player import Player
from .fishing_system import FishingSystem
import datetime
from .shop import Shop
from .item import Item
from .equipment import Equipment
import json
from .monopoly import MonopolySystem

@plugins.register(
    name="Game",
    desc="一个简单的文字游戏系统",
    version="0.2",
    author="assistant",
    desire_priority=0
)
class Game(Plugin):
    # 将 STANDARD_FIELDS 定义为类变量
    STANDARD_FIELDS = [
        'user_id', 'nickname', 'gold', 'level', 'last_checkin',
        'inventory', 'hp', 'max_hp', 'attack', 'defense', 'exp', 
        'last_fishing', 'rod_durability', 'equipped_weapon', 'equipped_armor',
        'last_item_use', 'spouse', 'marriage_proposal', 'last_attack',
        'position'
    ]

    # 添加开关机状态和进程锁相关变量
    PROCESS_LOCK_FILE = "game_process.lock"
    game_status = True  # 游戏系统状态
    scheduled_tasks = {}  # 定时任务字典

    # 添加新的类变量
    REMINDER_COST = 50  # 每条提醒消息的费用
    REMINDER_DURATION = 24 * 60 * 60  # 提醒持续时间(24小时)
    
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        
        # 添加进程锁和状态恢复逻辑
        try:
            self.data_dir = os.path.join(os.path.dirname(__file__), "data")
            os.makedirs(self.data_dir, exist_ok=True)
            
            # 初始化进程锁文件路径
            self.process_lock_file = os.path.join(self.data_dir, self.PROCESS_LOCK_FILE)
            
            # 恢复游戏状态和定时任务
            self._restore_game_state()
            
            # 确保数据目录"""  """存在
            self.player_file = os.path.join(self.data_dir, "players.csv")
            self.shop_file = os.path.join(self.data_dir, "shop_items.csv")
            
            # 初始化物品系统
            self.item_system = Item(self.data_dir)
            self.item_system.init_default_items()
            
            # 初始化商店数据文件
            if not os.path.exists(self.shop_file):
                with open(self.shop_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['name', 'price'])
                    # 写入默认商品
                    default_items = [
                        ['木剑', '100'],
                        ['铁剑', '300'],
                        ['布甲', '150'],
                        ['铁甲', '400'],
                        ['面包', '20'],
                        ['药水', '50'],
                        ['道生羽的节操', '1'],
                        ['木制鱼竿', '200'],
                        ['铁制鱼竿', '500'],
                        ['金制鱼竿', '1000']
                    ]
                    writer.writerows(default_items)
            
            # 初始化玩家数据文件
            if not os.path.exists(self.player_file):
                with open(self.player_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.STANDARD_FIELDS)
            
            # 初始化钓鱼系统
            self.fishing_system = FishingSystem(self.data_dir)
            self.shop = Shop(self)
            
            # 初始化装备系统
            self.equipment_system = Equipment(self)
            
            # 初始化提醒系统
            self.reminders = {}  # 格式: {user_id: {'content': str, 'expire_time': int}}
            self._load_reminders()  # 从文件加载提醒
            
            # 初始化配置文件
            config_file = os.path.join(self.data_dir, "config.json")
            if not os.path.exists(config_file):
                default_config = {
                    "admins": ["xxx"]  # 默认管理员列表
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
            
            # 初始化大富翁系统
            self.monopoly = MonopolySystem(self.data_dir)
            
        except Exception as e:
            logger.error(f"初始化游戏系统出错: {e}")
            raise
    
    def _migrate_data_files(self):
        """数据文件迁移和兼容性检查"""
        # 标准字段列表
        standard_player_fields = [
            'user_id', 'nickname', 'gold', 'level', 'last_checkin', 
            'inventory', 'hp', 'max_hp', 'attack', 'defense', 'exp',
            'last_fishing', 'rod_durability', 'equipped_weapon', 'equipped_armor',
            'last_item_use', 'spouse', 'marriage_proposal', 'last_attack'
        ]
        
        # 默认值设置
        default_values = {
            'gold': '0',
            'level': '1',
            'hp': '100',
            'max_hp': '100',
            'attack': '10',
            'defense': '5',
            'exp': '0',
            'inventory': '[]',
            'rod_durability': '{}',
            'equipped_weapon': '',
            'equipped_armor': '',
            'last_item_use': '0',
            'spouse': '',
            'marriage_proposal': '',
            'last_attack': '0'
        }
        
        if os.path.exists(self.player_file):
            try:
                # 读取所有现有数据
                all_players = {}
                with open(self.player_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictdReader(f)
                    for row in reader:
                        # 跳过空行或无效数据
                        if not row.get('user_id') and not row.get('nickname'):
                            continue
                        
                        # 使用user_id作为主键，如果没有user_id则使用nickname
                        key = row.get('user_id') or row.get('nickname')
                        if not key:
                            continue
                        
                        # 如果已存在玩家记录，合并数据
                        if key in all_players:
                            # 保留非空值
                            for field in standard_player_fields:
                                if row.get(field):
                                    all_players[key][field] = row[field]
                        else:
                            # 创建新记录
                            player_data = default_values.copy()
                            for field in standard_player_fields:
                                if row.get(field):
                                    player_data[field] = row[field]
                            all_players[key] = player_data
                            
                            # 确保user_id和nickname字段
                            if row.get('user_id'):
                                player_data['user_id'] = row['user_id']
                            if row.get('nickname'):
                                player_data['nickname'] = row['nickname']
                
                # 写入整理后的数据
                with open(self.player_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=standard_player_fields)
                    writer.writeheader()
                    for player_data in all_players.values():
                        # 确保所有必要字段都存在
                        for field in standard_player_fields:
                            if field not in player_data:
                                player_data[field] = default_values.get(field, '')
                        writer.writerow(player_data)
                        
            except Exception as e:
                logger.error(f"数据迁移出错: {e}")
                # 创建备份
                backup_file = f"{self.player_file}.bak"
                if os.path.exists(self.player_file):
                    import shutil
                    shutil.copy2(self.player_file, backup_file)

    def _load_reminders(self):
        """从文件加载提醒数据"""
        reminder_file = os.path.join(self.data_dir, "reminders.json")
        if os.path.exists(reminder_file):
            try:
                with open(reminder_file, 'r', encoding='utf-8') as f:
                    self.reminders = json.load(f)
                # 清理过期提醒
                current_time = int(time.time())
                self.reminders = {
                    k: v for k, v in self.reminders.items() 
                    if v['expire_time'] > current_time
                }
            except Exception as e:
                logger.error(f"加载提醒数据出错: {e}")
                self.reminders = {}

    def _save_reminders(self):
        """保存提醒数据到文件"""
        reminder_file = os.path.join(self.data_dir, "reminders.json")
        try:
            with open(reminder_file, 'w', encoding='utf-8') as f:
                json.dump(self.reminders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存提醒数据出错: {e}")

    def set_reminder(self, user_id, content):
        """设置提醒"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        if len(content.split()) < 2:
            return "请使用正确的格式：提醒 内容"
            
        reminder_content = ' '.join(content.split()[1:])
        # 去除感叹号和加号
        reminder_content = reminder_content.replace('!', '').replace('！', '').replace('+', '')
        
        if len(reminder_content) > 50:  # 限制提醒长度
            return "提醒内容不能超过50个字符"
            
        # 检查金币是否足够
        if int(player.gold) < self.REMINDER_COST:
            return f"设置提醒需要{self.REMINDER_COST}金币，的金币不足"
            
        # 扣除金币
        new_gold = int(player.gold) - self.REMINDER_COST
        self._update_player_data(user_id, {'gold': str(new_gold)})
        
        # 保存提醒
        self.reminders[user_id] = {
            'content': reminder_content,
            'expire_time': int(time.time()) + self.REMINDER_DURATION
        }
        self._save_reminders()
        
        return f"提醒设置成功！消息将在24小时内显示在每条游戏回复后面\n花费: {self.REMINDER_COST}金币"

    def get_active_reminders(self):
        """获取所有有效的提醒"""
        current_time = int(time.time())
        active_reminders = []
        
        for user_id, reminder in self.reminders.items():
            if reminder['expire_time'] > current_time:
                player = self.get_player(user_id)
                if player:
                    active_reminders.append(f"[{player.nickname}]: {reminder['content']}")
                    
        return "\n".join(active_reminders) if active_reminders else ""

    def on_handle_context(self, e_context: EventContext):
        if e_context['context'].type != ContextType.TEXT:
            return
            
        # 在处理任何命令前，先检查定时任务
        self._check_scheduled_tasks()  # 添加这一行
        
        content = e_context['context'].content.strip()
        msg: ChatMessage = e_context['context']['msg']
        
        # 使用昵称作为主要标识符
        nickname = msg.actual_user_nickname if msg.is_group else msg.from_user_nickname
        if not nickname:
            return "无法获取您的昵称，请确保昵称已设置"
        if not self.game_status and content not in ['注册', '开机', '关机', '定时', '查看定时', '取消定时', '清空定时']:
            return "游戏系统当前已关闭"
        # 获取当前ID用于日志记录
        current_id = msg.actual_user_id if msg.is_group else msg.from_user_id
        logger.debug(f"当前用户信息 - nickname: {nickname}, current_id: {current_id}")
        
        # 使用字典映射命令到处理函数
        cmd_handlers = {
            "注册": lambda n, i: self.register_player(n, i),
            "状态": lambda n, i: self.get_player_status(n),
            "个人状态": lambda n, i: self.get_player_status(n),
            "签到": lambda n, i: self.daily_checkin(n),
            "商店": lambda n, i: self.shop.show_shop(content),
            "购买": lambda n, i: self.shop.buy_item(n, content),
            "背包": lambda n, i: self.show_inventory(n),
            "装备": lambda n, i: self.equip_from_inventory(n, content),
            "游戏菜单": lambda n, i: self.game_help(),
            "赠送": lambda n, i: self.give_item(n, content, msg),
            "钓鱼": lambda n, i: self.fishing(n),  
            "图鉴": lambda n, i: self.show_fish_collection(n, content),
            "出售": lambda n, i: self.shop.sell_item(n, content),
            "批量出售": lambda n, i: self.shop.sell_item(n, content),
            "外出": lambda n, i: self.go_out(n),
            "使用": lambda n, i: self.use_item(n, content),
            "更新用户ID": lambda n, i: self.update_user_id(n, content),
            "排行榜": lambda n, i: self.show_leaderboard(n, content),
            "求婚": lambda n, i: self.propose_marriage(n, content, msg),
            "同意求婚": lambda n, i: self.accept_marriage(n),
            "拒绝求婚": lambda n, i: self.reject_marriage(n),
            "离婚": lambda n, i: self.divorce(n),
            "攻击": lambda n, i: self.attack_player(n, content, msg),
            "开机": lambda n, i: self.toggle_game_system(n, 'start'),
            "关机": lambda n, i: self.toggle_game_system(n, 'stop'),
            "定时": lambda n, i: self.schedule_game_system(n, content),
            "查看定时": lambda n, i: self.show_scheduled_tasks(n),
            "取消定时": lambda n, i: self.cancel_scheduled_task(n, content),
            "清空定时": lambda n, i: self.clear_scheduled_tasks(n),
            "提醒": lambda n, i: self.set_reminder(n, content),
            "删除提醒": lambda n, i: self.delete_reminder(n),
            "购买地块": lambda n, i: self.buy_property(n),
            "升级地块": lambda n, i: self.upgrade_property(n),
            "我的地产": lambda n, i: self.show_properties(n),
            "地图": lambda n, i: self.show_map(n),
        }
        
        cmd = content.split()[0]
        if cmd in cmd_handlers:
            reply = cmd_handlers[cmd](nickname, current_id)
            # 添加活动提醒
            reminders = self.get_active_reminders()
            if reminders:
                reply += f"\n\n📢 当前提醒:\n{reminders}"
                reply += "\n📢 如何使用提醒:\n设置提醒: 提醒 内容"
            e_context['reply'] = Reply(ReplyType.TEXT, reply)
            e_context.action = EventAction.BREAK_PASS
        else:
            e_context.action = EventAction.CONTINUE

    def game_help(self):
        import time
        return """
🎮 游戏指令大全 🎮

基础指令
————————————
📝 注册 - 注册新玩家
📊 状态 - 查看当前状态
📅 签到 - 每日签到领取金币

物品相关
————————————
🏪 商店 - 查看商店物品
💰 购买 [物品名] - 购买物品
🎒 背包 - 查看背包物品
⚔️ 装备 [物品名] - 装备物品
🎁 赠送 [@用户] [物品名] [数量] - 赠送物品
💊 使用 [物品名] - 使用消耗品

交易相关
————————————
💸 出售 [物品名] [数量] - 出售物品(原价60%)
📦 批量出售 [类型] - 批量出售背包物品

冒险相关
————————————
🎣 钓鱼 - 进行钓鱼获取金币
📖 图鉴 - 查看鱼类图鉴
🌄 外出 - 外出探险冒险
👊 攻击 [@用户] - 攻击其他玩家
🗺️ 地图 - 查看游戏地图

地产相关
————————————
🏠 我的地产 - 查看玩家地产
🏘️ 购买地块 - 购买地块
🏘️ 升级地块 - 升级地块

社交系统
————————————
💕 求婚 [@用户] - 向玩家求婚
💑 同意求婚 - 同意求婚请求
💔 拒绝求婚 - 拒绝求婚请求
⚡️ 离婚 - 解除婚姻关系

其他功能
————————————
🏆 排行榜 [类型] - 查看排行榜
🔄 更新用户ID [昵称] - 更新用户ID
🔔 提醒 [内容] - 设置提醒
🗑️ 删除提醒 - 删除提醒

管理员功能
————————————
🔧 开机 - 开启游戏系统
🔧 关机 - 关闭游戏系统
⏰ 定时 [开机/关机] [时间] [每天] - 设置定时任务
📋 查看定时 - 查看定时任务
❌ 取消定时 [开机/关机] [时间] - 取消定时任务
🗑️ 清空定时 - 清空所有定时任务

系统时间: {}
""".format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()))

    def update_user_id(self, user_id, content):
        """
        根据用户昵称更新用户ID
        
        Args:
            user_id (str): 当前用户ID
            content (str): 完整的命令内容
        
        Returns:
            str: 更新结果提示
        """
        # 检查命令格式
        try:
            parts = content.split()
            if len(parts) != 2:
                return "更新用户ID格式错误！请使用: 更新用户ID 昵称"
            
            target_nickname = parts[1]
        except Exception:
            return "更新用户ID格式错误！请使用: 更新用户ID 昵称"
        
        # 检查昵称长度
        if len(target_nickname) < 2 or len(target_nickname) > 20:
            return "昵称长度应在2-20个字符之间"
        
        # 读取所有数据
        rows = []
        updated = False
        
        try:
            with open(self.player_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                # 检查是否已存在相同的user_id
                for row in reader:
                    if row['user_id'] == str(user_id):
                        return "当前用户ID已存在，无法更新"
                    rows.append(row)
            
            # 重新遍历寻找目标昵称
            target_found = False
            for row in rows:
                if row['nickname'] == target_nickname:
                    if target_found:  # 如果已经找到过一次
                        return f"发现多个使用 {target_nickname} 昵称的用户，无法自动更新"
                    row['user_id'] = str(user_id)  # 更新user_id
                    updated = True
                    target_found = True
            
            if not target_found:
                return f"未找到昵称为 {target_nickname} 的用户"
            
            # 写入更新后的数据
            if updated:
                with open(self.player_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)
                
                return f"成功将昵称为 {target_nickname} 的用户ID更新为 {user_id}"
        
        except Exception as e:
            logger.error(f"更新用户ID出错: {e}")
            return "更新用户ID时发生错误"

    def register_player(self, nickname, current_id):
        """注册新玩家"""
        if not nickname or not current_id:
            return "无法获取您的昵称或ID，请确保昵称和ID已设置"
        
        # 检查昵称长度
        if len(nickname) < 2 or len(nickname) > 20:
            return "昵称长度应在2-20个字符之间"
        
        # 检查是否已注册
        if self.get_player(nickname) or self.get_player(current_id):
            return "您已经注册过了"
        
        try:
            # 创建新玩家
            player = Player.create_new(current_id, nickname)
            player.player_file = self.player_file
            player.standard_fields = self.STANDARD_FIELDS
            
            # 验证数据
            if not player.validate_data():
                raise ValueError("玩家数据验证失败")
                
            # 保存数据
            player.save_player_data(self.player_file, self.STANDARD_FIELDS)
            
            return f"注册成功! 欢迎 {nickname}"
            
        except Exception as e:
            logger.error(f"注册玩家出错: {e}")
            return f"注册失败: {str(e)}"

    def get_player(self, user_id) -> Optional[Player]:
        """获取玩家数据"""
        try:
            player = Player.get_player(user_id, self.player_file)
            if player:
                # 设置必要的文件信息
                player.player_file = self.player_file
                player.standard_fields = self.STANDARD_FIELDS
            return player
        except Exception as e:
            logger.error(f"获取玩家数据出错: {e}")
            raise

    def fishing(self, user_id):
        """钓鱼"""
        player = self.get_player(user_id)
        if not player:
            return "您还没注册,请先注册.如确定自己注册过，可能存在用户错误的bug。请发送更新用户ID，具体使用办法可发送游戏菜单"
            
        # 检查是否有鱼竿
        inventory = player.inventory
        rod = None
        for item in inventory:
            if item in ['木制鱼竿', '铁制鱼竿', '金制鱼竿']:
                rod = item
                break
                
        if not rod:
            return "您需要先购买一个鱼竿才能钓鱼"
            
        # 检查冷却时间
        now = datetime.datetime.now()
        last_fishing_str = player.last_fishing
        
        if last_fishing_str:
            last_fishing = datetime.datetime.strptime(last_fishing_str, '%Y-%m-%d %H:%M:%S')
            cooldown = datetime.timedelta(minutes=3)  # 3分钟冷却时间
            if now - last_fishing < cooldown:
                remaining = cooldown - (now - last_fishing)
                return f"钓鱼冷却中，还需等待 {remaining.seconds} 秒"
        
        # 调用钓鱼系统
        result = self.fishing_system.go_fishing(player, rod)
        
        # 更新玩家数据
        updates = {
            'last_fishing': now.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 处理耐久度
        rod_durability = player.rod_durability
        new_durability = max(0, rod_durability.get(rod, 100) - result['durability_cost'])
        rod_durability[rod] = new_durability
        updates['rod_durability'] = json.dumps(rod_durability)
        
        # 如果钓到鱼
        if result['success']:
            new_inventory = inventory + [result['fish']['name']]
            updates['inventory'] = json.dumps(new_inventory)
            # 添加金币奖励
            new_gold = int(player.gold) + result['coins_reward']
            updates['gold'] = str(new_gold)
            message = result['message']  # 使用钓鱼系返回的完整消息
        else:
            message = result['message']
            
        # 处理鱼竿损坏
        if new_durability <= 0:
            inventory.remove(rod)
            updates['inventory'] = json.dumps(inventory)
            durability_warning = f"\n💔 {rod}已损坏，已从背包移除"
        elif new_durability < 30:
            durability_warning = f"\n⚠️警告：{rod}耐久度不足30%"
        else:
            durability_warning = ""
            
        self._update_player_data(user_id, updates)
        return f"{message}{durability_warning}"

    def show_fish_collection(self, user_id, content=""):
        """显示鱼类图鉴"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册,请先注册.如确定自己注册过，可能存在用户错误的bug。请发送更新用户ID，具体使用办法可发送游戏菜单"
            
        # 解析命令参数
        parts = content.split()
        page = 1
        search_term = ""
        
        if len(parts) > 1:
            if parts[1].isdigit():
                page = int(parts[1])
            else:
                search_term = parts[1]
                
        return self.fishing_system.show_collection(player, page, search_term)

    #  外出打怪
    def go_out(self, user_id):
        """外出探险或漫步"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        # 检查玩家状态
        if int(player.hp) <= 0:
            return "您的生命值不足，请先使用药品恢复"
            
        # 检查冷却时间
        current_time = int(time.time())
        last_attack_time = int(player.last_attack)
        cooldown = 60
        
        if current_time - last_attack_time < cooldown:
            remaining = cooldown - (current_time - last_attack_time)
            return f"您刚刚进行过活动,请等待 {remaining} 秒后再次外出"

        # 掷骰子
        steps = self.monopoly.roll_dice()
        
        # 获取当前位置
        current_position = int(player.position) if hasattr(player, 'position') else 0
        new_position = (current_position + steps) % self.monopoly.map_data["total_blocks"]
        
        # 获取地块信息
        block = self.monopoly.get_block_info(new_position)
        
        # 更新玩家位置
        self._update_player_data(user_id, {
            'position': str(new_position),
            'last_attack': str(current_time)
        })
        
        result = [
            f"🎲 掷出了 {steps} 点",
            f"来到了 {block['name']}"
        ]
        
        # 根据地块类型处理不同情况
        if block['type'] == '起点':
            bonus = 200
            new_gold = int(player.gold) + bonus
            self._update_player_data(user_id, {'gold': str(new_gold)})
            result.append(f"经过起点获得 {bonus} 金币")
            
        elif block['type'] == '森林':
            # 触发战斗
            battle_result = self._battle(user_id, self._generate_monster(player))
            result.append(battle_result)
            
        elif block['type'] == '机遇':
            event = self.monopoly.trigger_random_event()
            if 'effect' in event:
                for key, value in event['effect'].items():
                    if key == 'gold':
                        new_gold = int(player.gold) + value
                        self._update_player_data(user_id, {'gold': str(new_gold)})
                        # 添加金币变化提示
                        if value > 0:
                            result.append(f"💰 获得 {value} 金币")
                        else:
                            result.append(f"💸 失去 {abs(value)} 金币")
            result.append(f"🎲 触发事件: {event['name']}")
            result.append(event['description'])
            
        elif block['type'] in ['空地', '直辖市', '省会', '地级市', '县城', '乡村']:
            owner = self.monopoly.get_property_owner(new_position)
            if owner is None:
                # 可以购买
                price = self.monopoly.calculate_property_price(new_position)
                result.append(f"这块地还没有主人")
                result.append(f"区域类型: {block['region']}")
                result.append(f"需要 {price} 金币购买")
                result.append("发送'购买地块'即可购买")
            else:
                # 需要付租金
                if owner != user_id:
                    rent = self.monopoly.calculate_rent(new_position)
                    if int(player.gold) >= rent:
                        new_gold = int(player.gold) - rent
                        owner_player = self.get_player(owner)
                        if owner_player:
                            owner_new_gold = int(owner_player.gold) + rent
                            self._update_player_data(owner, {'gold': str(owner_new_gold)})
                        self._update_player_data(user_id, {'gold': str(new_gold)})
                        result.append(f"这是 {owner_player.nickname if owner_player else owner} 的地盘")
                        result.append(f"区域类型: {block['region']}")
                        result.append(f"支付租金 {rent} 金币")
                    else:
                        result.append("你的金币不足以支付租金！")
                else:
                    result.append("这是你的地盘")
                    result.append(f"区域类型: {block['region']}")
                    if self.monopoly.properties_data[str(new_position)]["level"] < 3:
                        result.append("可以发送'升级地块'进行升级")
        
        return "\n".join(result)

    def _generate_monster(self, player):
        """根据玩家等级生成怪物"""
        player_level = int(player.level)
        level_factor = 1 + (player_level - 1) * 0.2
        
        monsters = [
            {
                'name': '森林史莱姆',
                'hp': int(60 * level_factor),
                'attack': int(10 * level_factor),
                'defense': int(6 * level_factor),
                'exp': int(20 * level_factor),
                'gold': int(30 * level_factor)
            },
            # ... 其他森林怪物
        ]
        
        monster = random.choice(monsters)
        if random.random() < 0.15:  # 15%概率变异
            monster['name'] = f"变异{monster['name']}"
            monster['hp'] = int(monster['hp'] * 1.5)
            monster['attack'] = int(monster['attack'] * 1.3)
            monster['defense'] = int(monster['defense'] * 1.2)
            monster['exp'] = int(monster['exp'] * 1.5)
            monster['gold'] = int(monster['gold'] * 1.5)
            
        return monster

    def _battle(self, user_id, monster):
        """战斗系统"""
        player = self.get_player(user_id)
        
        player_hp = int(player.hp)
        player_attack = int(player.attack)
        player_defense = int(player.defense)
        
        monster_hp = monster['hp']
        monster_max_hp = monster['hp']
        monster_defense = monster['defense']  # 获取怪物防御值
        
        battle_log = [f"⚔️ 遭遇了 {monster['name']}"]
        battle_log.append(f"怪物属性:")
        battle_log.append(f"❤️ 生命值: {monster['hp']}")
        battle_log.append(f"⚔️ 攻击力: {monster['attack']}")
        battle_log.append(f"🛡️ 防御力: {monster['defense']}")
        
        # 怪物是否狂暴状态
        is_berserk = False
        
        round_num = 1
        important_events = []
        while player_hp > 0 and monster_hp > 0:
            # 玩家攻击
            damage = max(1, player_attack - monster_defense)  # 使用monster_defense
            weapon_bonus = self.equipment_system.get_weapon_bonus(player)
            armor_reduction = self.equipment_system.get_armor_reduction(monster)
            final_damage = max(1, (damage + weapon_bonus) * (1 - armor_reduction))
            damage = int(final_damage * random.uniform(0.8, 1.2))
            monster_hp -= damage
            
            if round_num <= 5:
                battle_log.append(f"\n第{round_num}回合")
                battle_log.append(f"你对{monster['name']}造成 {damage} 点伤害")
            
            # 检查怪物是否进入狂暴状态
            if not is_berserk and monster_hp < monster_max_hp * 0.3 and random.random() < 0.4:
                is_berserk = True
                monster['attack'] = int(monster['attack'] * 1.5)
                if round_num <= 5:
                    battle_log.append(f"💢 {monster['name']}进入狂暴状态！")
                else:
                    important_events.append(f"第{round_num}回合: {monster['name']}进入狂暴状态！")
            
            # 怪物反击
            if monster_hp > 0:
                damage_multiplier = random.uniform(0.8, 1.2)
                base_damage = max(1, monster['attack'] - player_defense)
                monster_damage = int(base_damage * damage_multiplier)
                player_hp -= monster_damage
                
                # 狂暴状态下吸血
                if is_berserk:
                    life_steal = int(monster_damage * 0.3)
                    monster_hp = min(monster_max_hp, monster_hp + life_steal)
                    if round_num <= 5:
                        battle_log.append(f"{monster['name']}对你造成 {monster_damage} 点伤害，并吸取了 {life_steal} 点生命值")
                else:
                    if round_num <= 5:
                        battle_log.append(f"{monster['name']}对你造成 {monster_damage} 点伤害")
            
            round_num += 1
            
        if round_num > 5:
            battle_log.append(f"\n战斗持续了{round_num}回合")
            if important_events:
                battle_log.append("重要事件:")
                battle_log.extend(important_events)
            
        if player_hp > 0:
            # 根据怪物等级增加经验值
            player_level = int(player.level)
            monster_level = int(monster['exp'] / 15) # 根据基础经验值估算怪物等级
            level_diff = monster_level - player_level
            exp_multiplier = 1.0
            
            if level_diff > 0:
                exp_multiplier = 1 + (level_diff * 0.2) # 每高一级增加20%经验
            elif level_diff < 0:
                exp_multiplier = max(0.2, 1 + (level_diff * 0.1)) # 每低一级减少10%经验,最低20%
                
            exp_gain = int(monster['exp'] * exp_multiplier)
            gold_gain = monster['gold']
            
            new_exp = int(float(player.exp)) + exp_gain
            new_gold = int(player.gold) + gold_gain
            level_up = False
            
            exp_needed = 100 * (1 + (int(player.level) - 1) * 0.5)
            if new_exp >= exp_needed:
                new_level = int(player.level) + 1
                new_exp -= exp_needed
                level_up = True
                
                # 使用固定增长值
                hp_increase = 50      # 每级+50血量
                attack_increase = 15  # 每级+15攻击
                defense_increase = 10 # 每级+10防御
                
                new_max_hp = int(player.max_hp) + hp_increase
                new_attack = int(player.attack) + attack_increase
                new_defense = int(player.defense) + defense_increase
                
                self._update_player_data(user_id, {
                    'level': str(new_level),
                    'max_hp': str(new_max_hp),
                    'attack': str(new_attack),
                    'defense': str(new_defense)
                })
            
            self._update_player_data(user_id, {
                'hp': str(player_hp),
                'exp': str(new_exp),
                'gold': str(new_gold)
            })
            
            battle_log.append(f"\n🎉 战斗胜利")
            if exp_multiplier != 1.0:
                battle_log.append(f"经验值倍率: x{exp_multiplier:.1f}")
            battle_log.append(f"获得 {exp_gain} 经验值")
            battle_log.append(f"获得 {gold_gain} 金币")
            
            if level_up:
                battle_log.append(f"\n🆙 升级啦！当前等级 {new_level}")
                battle_log.append("属性提升：")
                battle_log.append(f"❤️ 生命上限 +{hp_increase}")
                battle_log.append(f"⚔️ 攻击力 +{attack_increase}")
                battle_log.append(f"🛡️ 防御力 +{defense_increase}")
        else:
            self._update_player_data(user_id, {'hp': '0'})
            battle_log.append(f"\n💀 战斗失败")
            battle_log.append("你被打倒了，需要使用药品恢复生命值")
        
        return "\n".join(battle_log)
    
    def use_item(self, user_id, content):
        """使用物品功能"""
        try:
            # 解析命令，格式为 "使用 物品名" 或 "使用 物品名 数量"
            parts = content.split()
            if len(parts) < 2:
                return "使用格式错误！请使用: 使用 物品名 [数量]"
            
            item_name = parts[1]
            amount = 1  # 默认使用1个
            if len(parts) > 2:
                amount = int(parts[2])
                if amount <= 0:
                    return "使用数量必须大于0"
        except (IndexError, ValueError):
            return "使用格式错误！请使用: 使用 物品名 [数量]"
        
        # 检查玩家是否存在
        player = self.get_player(user_id)
        if not player:
            return "您还没注册,请先注册.如确定自己注册过，可能存在用户错误的bug。请发送更新用户ID，具体使用办法可发送游戏菜单"
        
        # 获取物品信息
        items = self.get_shop_items()
        if item_name not in items:
            return "没有这个物品"
        
        # 检查背包中是否有足够的物品
        inventory = player.inventory  # 直接使用列表，不需要json.loads
        item_count = inventory.count(item_name)
        if item_count < amount:
            return f"背包中只有 {item_count} 个 {item_name}"
        
        # 获取物品类型和效果
        item = items[item_name]
        
        # 判断物品类型
        if item.get('type') != 'consumable':
            return "该物品不能直接使用"
        
        # 计算恢复效果
        current_hp = int(player.hp)
        max_hp = int(player.max_hp)
        heal_amount = int(item.get('hp', 0)) * amount
        
        # 计算新的生命值
        new_hp = min(current_hp + heal_amount, max_hp)
        
        # 从背包中移除物品
        for _ in range(amount):
            inventory.remove(item_name)
        
        # 添加物品使用冷却时间
        current_time = int(time.time())
        try:
            last_use = player.last_item_use
        except AttributeError:
            # 如果属性不存在，则默认为0
            last_use = 0
        
        if current_time - int(last_use) < 5:  # 5秒冷却时间
            return f"物品使用太频繁，请等待{5 - (current_time - int(last_use))}秒"
        
        # 更新玩家数据时添加使用时间
        updates = {
            'inventory': json.dumps(inventory),
            'hp': str(new_hp),
            'last_item_use': str(current_time)
        }
        
        # 如果玩家数据中没有last_item_use字段，确保它被添加到标准字段中
        if hasattr(player, 'standard_fields') and player.standard_fields and 'last_item_use' not in player.standard_fields:
            player.standard_fields.append('last_item_use')
        
        player.update_data(updates)
        
        return f"使用 {amount} 个 {item_name}，恢复 {new_hp - current_hp} 点生命值！\n当前生命值: {new_hp}/{max_hp}"
    
    
    def get_player_status(self, user_id):
        """获取玩家状态"""
        player = self.get_player(user_id)
        if not player:
            return "您还没注册,请先注册.如确定自己注册过，可能存在用户错误的bug。请发送更新用户ID，具体使用办法可发送游戏菜单"
        
        # 获取物品信息
        items_info = self.item_system.get_all_items()
        
        # 使用Player类的get_player_status方法
        return player.get_player_status(items_info)

    def daily_checkin(self, user_id):
        """每日签到"""
        try:
            player = self.get_player(user_id)
            if not player:
                return "您还没注册,请先注册.如确定自己注册过，可能存在用户错误的bug。请发送更新用户ID，具体使用办法可发送游戏菜单"
            
            import datetime
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            
            # 检查签到状态
            if player.last_checkin == today:
                return "您今天已经签到过了"
            
            # 计算奖励
            reward = 50  # 签到奖励50金币
            exp_reward = 10  # 签到奖励10经验
            
            # 更新数据
            updates = {
                'gold': player.gold + reward,
                'exp': player.exp + exp_reward,
                'last_checkin': today
            }
            
            self._update_player_data(user_id, updates)
            
            return f"签到成功 获得{reward}金币，经验{exp_reward}，当前金币: {player.gold + reward}"
            
        except Exception as e:
            logger.error(f"签到出错: {e}")
            return f"签到失败: {str(e)}"

    def get_shop_items(self) -> dict:
        """获取商店物品列表"""
        return self.item_system.get_shop_items()

    def give_item(self, user_id, content, msg: ChatMessage):
        # 解析命令参数
        parts = content.split()
        if len(parts) < 4:
            return "格式错误！请使用: 赠送 @用户 物品名 数量"
        
        # 获取被赠送者ID
        if not msg.is_group:
            return "只能在群聊中使用赠送功能"
        
        target_id = None
        # 解析@后面的用户名
        for part in parts:
            if part.startswith('@'):
                target_name = part[1:]  # 去掉@符号
                # 遍历players.csv查找匹配的用户
                with open(self.player_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row['nickname'] == target_name:
                            target_id = row['user_id']
                            break
                break  # 找到第一个@用户后就退出

        if not target_id:
            return "无法找到目标用户，请确保该用户已注册游戏"

        # 从消息内容中提取物品名和数量
        # 跳过第一个词"赠送"和@用户名
        remaining_parts = [p for p in parts[1:] if not p.startswith('@')]
        if len(remaining_parts) < 2:
            return "请指定物品名称和数量"
        
        item_name = remaining_parts[0]
        try:
            amount = int(remaining_parts[1])
            if amount <= 0:
                return "赠送数量必须大于0"
        except (IndexError, ValueError):
            return "请正确指定赠送数量"
        
        # 检查双方是否都已注册
        sender = self.get_player(user_id)
        if not sender:
            return "您还没注册,请先注册.如确定自己注册过，可能存在用错误的bug。请发送更新用户ID，具体使用办法可发送游戏菜单"
        
        receiver = self.get_player(target_id)
        if not receiver:
            return "对方还没有注册游戏"
        
        # 检查发送者是否拥有足够的物品
        sender_inventory = sender.inventory
        equipped_count = 0
        
        # 检查是否是装备中的物品
        if item_name == sender.equipped_weapon or item_name == sender.equipped_armor:
            equipped_count = 1
        
        # 计算可赠送数量（排除装备的物品）
        available_count = sender_inventory.count(item_name) - equipped_count
        
        if available_count < amount:
            if equipped_count > 0:
                return f"背包中只有 {available_count} 个未装备的 {item_name}，无法赠送 {amount} 个"
            else:
                return f"背包中只有 {available_count} 个 {item_name}"
        
        # 更新双方的背包
        for _ in range(amount):
            sender_inventory.remove(item_name)
        
        receiver_inventory = receiver.inventory
        receiver_inventory.extend([item_name] * amount)
        
        # 保存更新
        self._update_player_data(user_id, {
            'inventory': sender_inventory
        })
        self._update_player_data(target_id, {
            'inventory': receiver_inventory
        })
        
        return f"成功将 {amount} 个 {item_name} 赠送给了 {receiver.nickname}"

    def show_leaderboard(self, user_id, content):
        """显示排行榜"""
        try:
            # 默认显示金币排行
            board_type = "金币"
            if content and len(content.split()) > 1:
                board_type = content.split()[1]
            
            if board_type not in ["金币", "等级"]:
                return "目前支持的排行榜类型：金币、等级"
            
            # 读取所有玩家数据
            players = []
            with open(self.player_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                players = list(reader)
            
            if not players:
                return "暂无玩家数据"
            
            # 安全的数值转换函数
            def safe_int(value, default=0):
                try:
                    # 先转换为浮点数，再转换为整数
                    return int(float(str(value).replace(',', '')))
                except (ValueError, TypeError):
                    return default
            
            # 根据类型排序
            if board_type == "金币":
                players.sort(key=lambda x: safe_int(x.get('gold', 0)), reverse=True)
                title = "金币排行榜"
                value_key = 'gold'
                suffix = "金币"
            else:  # 等级排行榜
                # 使用元组排序，先按等级后按经验
                players.sort(
                    key=lambda x: (
                        safe_int(x.get('level', 1)), 
                        safe_int(x.get('exp', 0))
                    ), 
                    reverse=True
                )
                title = "等级排行榜"
                value_key = 'level'
                suffix = "级"
            
            # 生成排行榜
            result = f"{title}:\n"
            result += "-" * 30 + "\n"
            
            # 只显示前10名
            for i, player in enumerate(players[:10], 1):
                nickname = player['nickname']
                value = safe_int(player[value_key])
                
                # 为等级排行榜添加经验值显示
                exp_info = f" (经验: {safe_int(player.get('exp', '0'))})" if board_type == "等级" else ""
                
                # 添加排名
                rank_mark = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                result += f"{rank_mark} {nickname}: {value}{suffix}{exp_info}\n"
            
            # 如果当前用户不在前10名，显示其排名
            current_player = next((p for p in players if p['nickname'] == user_id), None)
            if current_player:
                current_rank = players.index(current_player) + 1
                if current_rank > 10:
                    result += "-" * 30 + "\n"
                    value = current_player[value_key]
                    exp_info = f" (经验: {safe_int(current_player.get('exp', '0'))})" if board_type == "等级" else ""
                    result += f"你的排名: {current_rank}. {current_player['nickname']}: {value}{suffix}{exp_info}"
            
            return result
            
        except Exception as e:
            logger.error(f"显示排行榜出错: {e}")
            return "显示排行榜时发生错误"

    def propose_marriage(self, user_id, content, msg: ChatMessage):
        """求婚"""
        if not msg.is_group:
            return "只能在群聊中使用求婚功能"
        
        # 获取求婚者信息
        proposer = self.get_player(user_id)
        if not proposer:
            return "您还没有注册游戏"
        
        # 解析命令参数
        parts = content.split()
        if len(parts) < 2 or not parts[1].startswith('@'):
            return "请使用正确的格式：求婚 @用户名"
        
        target_name = parts[1][1:]  # 去掉@符号
        target = self.get_player(target_name)
        
        if not target:
            return "对方还没有注册游戏"
            
        if target.nickname == proposer.nickname:
            return "不能向自己求婚"
        
        # 检查是否已经是配偶
        proposer_spouses = proposer.spouse.split(',') if proposer.spouse else []
        if target.nickname in [s for s in proposer_spouses if s]:
            return "你们已经是夫妻了"
        
        if target.marriage_proposal:
            return "对方已经有一个待处理的求婚请求"
        
        # 更新目标玩家的求婚请求，使用求婚者的昵称
        self._update_player_data(target.nickname, {
            'marriage_proposal': proposer.nickname
        })
        
        return f"您向 {target_name} 发起了求婚请求，等待对方回应"

    def accept_marriage(self, user_id):
        """同意求婚"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
        
        proposal = player.marriage_proposal
        if not proposal:
            return "您没有待处理的求婚请求"
        
        # 使用昵称获取求婚者信息
        proposer = self.get_player(proposal)
        if not proposer:
            # 清除无效的求婚请求
            self._update_player_data(user_id, {
                'marriage_proposal': ''
            })
            return "求婚者信息不存在或已注销账号"
        
        # 获取现有配偶列表
        current_spouses = player.spouse.split(',') if player.spouse else []
        proposer_spouses = proposer.spouse.split(',') if proposer.spouse else []
        
        # 过滤掉空字符串
        current_spouses = [s for s in current_spouses if s]
        proposer_spouses = [s for s in proposer_spouses if s]
        
        # 添加新配偶
        current_spouses.append(proposer.nickname)
        proposer_spouses.append(player.nickname)
        
        # 更新双方的婚姻状态
        self._update_player_data(player.nickname, {
            'spouse': ','.join(current_spouses),
            'marriage_proposal': ''
        })
        self._update_player_data(proposer.nickname, {
            'spouse': ','.join(proposer_spouses)
        })
        
        return f"恭喜！您接受了 {proposer.nickname} 的求婚！现在你们是夫妻了！"

    def reject_marriage(self, user_id):
        """拒绝求婚"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
        
        proposal = player.marriage_proposal
        if not proposal:
            return "您没有待处理的求婚请求"
        
        # 清除求婚请求
        self._update_player_data(user_id, {
            'marriage_proposal': ''
        })
        
        return f"您拒绝了 {proposal} 的求婚请求"

    def divorce(self, user_id):
        """离婚"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
        
        # 获取所有配偶
        spouses = player.spouse.split(',') if player.spouse else []
        if not spouses:
            return "您还没有结婚"
            
        # 解除与所有配偶的婚姻关系
        for spouse_name in spouses:
            if spouse_name:
                spouse = self.get_player(spouse_name)
                if spouse:
                    # 从配偶的婚姻列表中移除当前玩家
                    spouse_list = spouse.spouse.split(',')
                    spouse_list = [s for s in spouse_list if s and s != player.nickname]
                    self._update_player_data(spouse_name, {
                        'spouse': ','.join(spouse_list)
                    })
        
        # 清空玩家的婚姻状态
        self._update_player_data(user_id, {
            'spouse': ''
        })
        
        return f"您已经与所有配偶离婚"

    def attack_player(self, user_id, content, msg: ChatMessage):
        """强制攻击其他玩家"""
        if not msg.is_group:
            return "只能在群聊中使用攻击功能"
        
        # 解析命令参数
        parts = content.split()
        if len(parts) < 2 or not parts[1].startswith('@'):
            return "请使用正确的格式：攻击 @用户名"
        
        target_name = parts[1][1:]  # 去掉@符号
        
        # 获取攻击者信息
        attacker = self.get_player(user_id)
        if not attacker:
            return "您还没有注册游戏"
        
        # 获取目标玩家信息
        target = self.get_player(target_name)
        if not target:
            return "目标玩家还没有注册游戏"
        
        # 不能攻击自己
        if attacker.nickname == target.nickname:
            return "不能攻击自己"
        
        # 检查冷却时间
        import time
        current_time = int(time.time())
        last_attack = int(attacker.last_attack)
        cooldown = 300  # 5分钟冷却
        
        if current_time - last_attack < cooldown:
            remaining = cooldown - (current_time - last_attack)
            return f"攻击冷却中，还需等待 {remaining} 秒"
        
        # 获取双方属性
        attacker_hp = int(attacker.hp)
        attacker_attack = int(attacker.attack)
        attacker_defense = int(attacker.defense)
        
        target_hp = int(target.hp)
        target_attack = int(target.attack)
        target_defense = int(target.defense)
        
        # 获取双方配偶信息
        attacker_spouses = []
        if attacker.spouse:
            for spouse_name in attacker.spouse.split(','):
                if spouse_name:
                    spouse = self.get_player(spouse_name)
                    if spouse:
                        attacker_spouses.append(spouse)
                        
        target_spouses = []
        if target.spouse:
            for spouse_name in target.spouse.split(','):
                if spouse_name:
                    spouse = self.get_player(spouse_name)
                    if spouse:
                        target_spouses.append(spouse)
        
        # 战斗日志
        battle_log = [
            "⚔️ PVP战斗开始 ⚔️\n",
            f"[{attacker.nickname}]",
            f"❤️生命: {attacker_hp}",
            f"⚔️攻击: {attacker_attack}",
            f"🛡️防御: {attacker_defense}\n",
            f"VS\n",
            f"[{target.nickname}]",
            f"❤️生命: {target_hp}",
            f"⚔️攻击: {target_attack}",
            f"🛡️防御: {target_defense}\n"
        ]
        
        # 战斗逻辑
        round_num = 1
        while attacker_hp > 0 and target_hp > 0:
            # 攻击者回合
            damage = max(1, attacker_attack - target_defense)
            weapon_bonus = self.equipment_system.get_weapon_bonus(attacker)
            armor_reduction = self.equipment_system.get_armor_reduction(target)
            final_damage = max(1, (damage + weapon_bonus) * (1 - armor_reduction))
            damage = int(final_damage * random.uniform(0.8, 1.2))
            target_hp -= damage  # 修改这里：从 monster_hp 改为 target_hp
            
            if round_num <= 5:
                battle_log.append(f"\n第{round_num}回合")
                battle_log.append(f"{attacker.nickname}对{target.nickname}造成 {damage} 点伤害")
            
            # 攻击者配偶协助(每个配偶30%概率)
            for spouse in attacker_spouses:
                if random.random() < 0.3:
                    spouse_attack = int(spouse.attack)
                    spouse_damage = max(1, spouse_attack - target_defense)
                    spouse_damage = int(spouse_damage * random.uniform(0.4, 0.6))
                    damage += spouse_damage
                    battle_log.append(f"回合 {round_num}: {spouse.nickname} 协助攻击,额外造成 {spouse_damage} 点伤害")
                
            target_hp -= damage
            battle_log.append(f"回合 {round_num}: {attacker.nickname} 对 {target.nickname} 造成 {damage} 点伤害")
            
            # 目标反击
            if target_hp > 0:
                damage = max(1, target_attack - attacker_defense)
                damage = int(damage * random.uniform(0.8, 1.2))
                
                # 目标配偶协助(每个配偶30%概率)
                for spouse in target_spouses:
                    if random.random() < 0.3:
                        spouse_attack = int(spouse.attack)
                        spouse_damage = max(1, spouse_attack - attacker_defense)
                        spouse_damage = int(spouse_damage * random.uniform(0.4, 0.6))
                        damage += spouse_damage
                        battle_log.append(f"回合 {round_num}: {spouse.nickname} 协助防御,额外造成 {spouse_damage} 点伤害")
                    
                attacker_hp -= damage
                battle_log.append(f"回合 {round_num}: {target.nickname} 对 {attacker.nickname} 造成 {damage} 点伤害")
            
            round_num += 1
            if round_num > 10:  # 限制最大回合数
                break
        
        # 计算惩罚金币比例(回合数越多惩罚越少)
        penalty_rate = max(0.2, 0.6 - (round_num - 1) * 0.05)  # 每回合减少5%,最低20%
        battle_log.append("\n战斗结果:")
        
        if attacker_hp <= 0:  # 攻击者失败
            # 扣除金币
            attacker_gold = int(attacker.gold)
            penalty_gold = int(attacker_gold * penalty_rate)
            new_attacker_gold = attacker_gold - penalty_gold
            new_target_gold = int(target.gold) + penalty_gold
            
            # 随机丢失物品
            attacker_items = attacker.inventory  # 直接使用inventory列表
            lost_item = None
            if attacker_items:
                lost_item = random.choice(attacker_items)
                attacker_items.remove(lost_item)
            
            # 更新数据
            self._update_player_data(user_id, {
                'hp': str(attacker_hp),
                'gold': str(new_attacker_gold),
                'inventory': attacker_items,  # _update_player_data会处理列表到JSON的转换
                'last_attack': str(current_time)
            })
            self._update_player_data(target.nickname, {
                'hp': str(target_hp),
                'gold': str(new_target_gold)
            })
            
            result = f"{target.nickname} 获胜!\n{attacker.nickname} 赔偿 {penalty_gold} 金币"
            if lost_item:
                result += f"\n{attacker.nickname} 丢失了 {lost_item}"
            
        else:  # 攻击者胜利
            # 扣除金币
            target_gold = int(target.gold)
            penalty_gold = int(target_gold * penalty_rate)
            new_target_gold = target_gold - penalty_gold
            new_attacker_gold = int(attacker.gold) + penalty_gold
            
            # 随机丢失物品
            target_items = target.inventory  # 直接使用inventory列表
            lost_item = None
            if target_items:
                lost_item = random.choice(target_items)
                target_items.remove(lost_item)
            
            # 更新数据
            self._update_player_data(target.nickname, {
                'hp': str(target_hp),
                'gold': str(new_target_gold),
                'inventory': target_items,  # _update_player_data会处理列表到JSON的转换
            })
            self._update_player_data(user_id, {
                'hp': str(attacker_hp),
                'gold': str(new_attacker_gold),
                'last_attack': str(current_time)
            })
            
            result = f"{attacker.nickname} 获胜!\n{target.nickname} 赔偿 {penalty_gold} 金币"
            if lost_item:
                result += f"\n{target.nickname} 丢失了 {lost_item}"
        
        battle_log.append(result)
        return "\n".join(battle_log)

    def _update_player_data(self, user_id, updates: dict):
        """更新玩家数据
        
        Args:
            user_id: 玩家ID或昵称
            updates: 需要更新的字段和值的字典
        """
        try:
            player = self.get_player(user_id)
            if not player:
                logger.error(f"找不到玩家: {user_id}")
                raise ValueError(f"找不到玩家: {user_id}")
                
            # 设置必要的文件信息
            player.player_file = self.player_file
            player.standard_fields = self.STANDARD_FIELDS
            
            # 数据类型转换和验证
            for key, value in updates.items():
                if isinstance(value, (int, float)):
                    updates[key] = str(value)
                elif isinstance(value, (list, dict)):
                    updates[key] = json.dumps(value)
                    
            # 使用Player类的update_data方法
            player.update_data(updates)
            
        except Exception as e:
            logger.error(f"更新玩家数据出错: {e}")
            raise






    def show_inventory(self, user_id):
        player = self.get_player(user_id)
        if not player:
            return "您还没注册..."
            
        items_info = self.item_system.get_all_items()
        return player.get_inventory_display(items_info)

    def equip_item(self, user_id: str, item_name: str) -> str:
        """装备物品的包装方法"""
        return self.equipment_system.equip_item(user_id, item_name)
    
    def unequip_item(self, user_id: str, item_type: str) -> str:
        """卸下装备的包装方法"""
        return self.equipment_system.unequip_item(user_id, item_type)

    def equip_from_inventory(self, user_id: str, content: str) -> str:
        """从背包装备物品
        
        Args:
            user_id: 玩家ID
            content: 完整的命令内容
            
        Returns:
            str: 装备结果提示
        """
        try:
            # 解析命令
            parts = content.split()
            if len(parts) < 2:
                return "装备格式错误！请使用: 装备 物品名"
                
            item_name = parts[1]
            
            # 调用装备系统的装备方法
            return self.equipment_system.equip_item(user_id, item_name)
            
        except Exception as e:
            logger.error(f"装备物品出错: {e}")
            return "装备物品时发生错误"
        except Exception as e:
            logger.error(f"装备物品出错: {e}")
            return "装备物品时发生错误"
            logger.error(f"装备物品出错: {e}")
            return "装备物品时发生错误"

    def _restore_game_state(self):
        """从进程锁文件恢复游戏状态"""
        try:
            if os.path.exists(self.process_lock_file):
                with open(self.process_lock_file, 'r') as f:
                    data = json.load(f)
                    self.game_status = data.get('game_status', True)
                    self.scheduled_tasks = data.get('scheduled_tasks', {})
                    
                    # 恢复定时任务
                    current_time = time.time()
                    for task_id, task in list(self.scheduled_tasks.items()):
                        if task['time'] <= current_time:
                            # 执行过期的定时任务
                            if task['action'] == 'start':
                                self.game_status = True
                            elif task['action'] == 'stop':
                                self.game_status = False
                            # 删除已执行的任务
                            del self.scheduled_tasks[task_id]
                    
                    # 保存更新后的状态
                    self._save_game_state()
        except Exception as e:
            logger.error(f"恢复游戏状态出错: {e}")
            self.game_status = True
            self.scheduled_tasks = {}

    def _save_game_state(self):
        """保存游戏状态到进程锁文件"""
        try:
            # 清理任务ID中的receiver信息
            cleaned_tasks = {}
            for task_id, task in self.scheduled_tasks.items():
                clean_task_id = task_id.split(',')[0]
                if clean_task_id not in cleaned_tasks:  # 避免重复任务
                    cleaned_tasks[clean_task_id] = task
            
            self.scheduled_tasks = cleaned_tasks
            
            with open(self.process_lock_file, 'w') as f:
                json.dump({
                    'game_status': self.game_status,
                    'scheduled_tasks': self.scheduled_tasks
                }, f)
        except Exception as e:
            logger.error(f"保存游戏状态出错: {e}")

    def toggle_game_system(self, user_id, action='toggle'):
        """切换游戏系统状态"""
        try:
            player = self.get_player(user_id)
            if not player:
                # 检查是否是默认管理员
                config_file = os.path.join(self.data_dir, "config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        if user_id not in config.get("admins", []):
                            return "您还没有注册游戏"
                else:
                    return "您还没有注册游戏"
            elif not self._is_admin(player):
                return "只有管理员才能操作游戏系统开关"
            
            if action == 'toggle':
                self.game_status = not self.game_status
            elif action == 'start':
                self.game_status = True
            elif action == 'stop':
                self.game_status = False
            
            self._save_game_state()
            return f"游戏系统已{'开启' if self.game_status else '关闭'}"
        except Exception as e:
            logger.error(f"切换游戏系统状态出错: {e}")
            return "操作失败，请检查系统状态"

    def schedule_game_system(self, user_id, content):
        """设置定时开关机"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        # 检查是否是管理员
        if not self._is_admin(player):
            return "只有管理员才能设置定时任务"
        
        try:
            # 解析命令格式: 定时 开机/关机 HH:MM [每天]
            parts = content.split()
            if len(parts) < 3:
                return "格式错误！请使用: 定时 开机/关机 HH:MM [每天]"
                
            action = '开机' if parts[1] == '开机' else '关机' if parts[1] == '关机' else None
            if not action:
                return "请指定正确的操作(开机/关机)"
                
            # 解析时间
            try:
                hour, minute = map(int, parts[2].split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                return "请输入正确的时间格式(HH:MM)"
                
            # 检查是否是每天执行
            is_daily = len(parts) > 3 and parts[3] == '每天'
            
            # 计算执行时间
            now = datetime.datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if not is_daily and target_time <= now:
                target_time += datetime.timedelta(days=1)
                
            # 生成任务ID，每天任务添加daily标记
            task_id = f"{'daily' if is_daily else ''}{action}_{target_time.strftime('%H%M')}"
            
            # 添加定时任务
            self.scheduled_tasks[task_id] = {
                'action': 'start' if action == '开机' else 'stop',
                'time': target_time.timestamp(),
                'is_daily': is_daily
            }
            
            self._save_game_state()
            daily_text = "每天 " if is_daily else ""
            return f"已设置{daily_text}{action}定时任务: {target_time.strftime('%H:%M')}"
            
        except Exception as e:
            logger.error(f"设置定时任务出错: {e}")
            return "设置定时任务失败"

    def _is_admin(self, player):
        """检查玩家是否是管理员"""
        try:
            config_file = os.path.join(self.data_dir, "config.json")
            if not os.path.exists(config_file):
                # 创建默认配置文件
                default_config = {
                    "admins": ["xxx"]  # 默认管理员列表
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
            
            # 读取配置文件
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return player.nickname in config.get("admins", [])
        except Exception as e:
            logger.error(f"读取管理员配置出错: {e}")
            return False

    def show_scheduled_tasks(self, user_id):
        """显示所有定时任务"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        if not self._is_admin(player):
            return "只有管理员才能查看定时任务"
        
        if not self.scheduled_tasks:
            return "当前没有定时任务"
        
        # 用于去重和整理任务的字典
        unique_tasks = {}
        
        result = "定时任务列表:\n" + "-" * 20 + "\n"
        for task_id, task in self.scheduled_tasks.items():
            # 清理掉可能包含的receiver信息
            clean_task_id = task_id.split(',')[0]
            
            action = "开机" if task['action'] == 'start' else "关机"
            time_str = datetime.datetime.fromtimestamp(task['time']).strftime('%H:%M')
            
            # 使用间和动作作为唯一键
            task_key = f"{time_str}_{action}"
            
            if task.get('is_daily'):
                task_desc = f"每天 {time_str}"
            else:
                task_desc = datetime.datetime.fromtimestamp(task['time']).strftime('%Y-%m-%d %H:%M')
                
            unique_tasks[task_key] = f"{action}: {task_desc}"
        
        # 按时间排序显示任务
        for task_desc in sorted(unique_tasks.values()):
            result += f"{task_desc}\n"
        
        return result

    def cancel_scheduled_task(self, user_id, content):
        """取消定时任务"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        if not self._is_admin(player):
            return "只有管理员才能取消定时任务"
        
        try:
            # 解析命令格式: 取消定时 开机/关机 HH:MM
            parts = content.split()
            if len(parts) != 3:
                return "格式错误！请使用: 取消定时 开机/关机 HH:MM"
                
            action = '开机' if parts[1] == '开机' else '关机' if parts[1] == '关机' else None
            if not action:
                return "请指定正确的操作(开机/关机)"
                
            # 解析时间
            try:
                hour, minute = map(int, parts[2].split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError
            except ValueError:
                return "请输入正确的时间格式(HH:MM)"
                
            # 生成任务ID格式
            now = datetime.datetime.now()
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target_time <= now:
                target_time += datetime.timedelta(days=1)
                
            task_id = f"{action}_{target_time.strftime('%Y%m%d%H%M')}"
            
            # 检查并删除任务
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]
                self._save_game_state()
                return f"已取消{action}定时任务: {target_time.strftime('%Y-%m-%d %H:%M')}"
            else:
                return f"未找到指定的定时任务"
            
        except Exception as e:
            logger.error(f"取消定时任务出错: {e}")
            return "取消定时任务失败"

    def _check_scheduled_tasks(self):
        """检查并执行到期的定时任务"""
        try:
            current_time = time.time()
            tasks_to_remove = []
            
            for task_id, task in self.scheduled_tasks.items():
                if task['time'] <= current_time:
                    # 执行定时任务
                    if task['action'] == 'start':
                        self.game_status = True
                        logger.info(f"定时任务执行：开机 - {datetime.datetime.fromtimestamp(task['time']).strftime('%Y-%m-%d %H:%M')}")
                    elif task['action'] == 'stop':
                        self.game_status = False
                        logger.info(f"定时任务执行：关机 - {datetime.datetime.fromtimestamp(task['time']).strftime('%Y-%m-%d %H:%M')}")
                    
                    if task.get('is_daily'):
                        # 更新每日任务的下一次执行时间
                        next_time = datetime.datetime.fromtimestamp(task['time']) + datetime.timedelta(days=1)
                        task['time'] = next_time.timestamp()
                    else:
                        # 将非每日任务添加到待删除列表
                        tasks_to_remove.append(task_id)
            
            # 删除已执行的非每日任务
            for task_id in tasks_to_remove:
                del self.scheduled_tasks[task_id]
                
            # 如果有任务被执行或更新，保存状态
            if tasks_to_remove or any(task.get('is_daily') for task in self.scheduled_tasks.values()):
                self._save_game_state()
            
        except Exception as e:
            logger.error(f"检查定时任务出错: {e}")

    def clear_scheduled_tasks(self, user_id):
        """清空所有定时任务"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        if not self._is_admin(player):
            return "只有管理员才能清空定时任务"
        
        try:
            task_count = len(self.scheduled_tasks)
            if task_count == 0:
                return "当前没有定时任务"
                
            self.scheduled_tasks.clear()
            self._save_game_state()
            return f"已清空 {task_count} 个定时任务"
            
        except Exception as e:
            logger.error(f"清空定时任务出错: {e}")
            return "清空定时任务失败"

    def delete_reminder(self, user_id):
        """删除提醒"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        if user_id not in self.reminders:
            return "您没有设置任何提醒"
            
        # 删除提醒
        del self.reminders[user_id]
        self._save_reminders()
        
        return "提醒已删除"

    def buy_property(self, user_id):
        """购买当前位置的地块"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        # 获取玩家当前位置
        current_position = int(getattr(player, 'position', 0))
        block = self.monopoly.get_block_info(current_position)
        
        # 检查是否是可购买的地块
        purchasable_types = ['空地', '直辖市', '省会', '地级市', '县城', '乡村']
        if block['type'] not in purchasable_types:
            return "当前位置不是可购买的地块"
            
        # 检查是否已被购买
        if self.monopoly.get_property_owner(current_position):
            return "这块地已经被购买了"
            
        # 计算地块价格
        base_prices = {
            '直辖市': 2000,
            '省会': 1500,
            '地级市': 1000,
            '县城': 500,
            '乡村': 300,
            '空地': 200
        }
        base_price = base_prices.get(block['type'], 500)
        distance_factor = 1 + (current_position // 10) * 0.2  # 每10格增加20%价格
        price = int(base_price * distance_factor)
        
        # 检查玩家金币是否足够
        if int(player.gold) < price:
            return f"购买这块地需要 {price} 金币，您的金币不足"
            
        # 扣除金币并购买地块
        new_gold = int(player.gold) - price
        if self.monopoly.buy_property(current_position, user_id, price):
            self._update_player_data(user_id, {'gold': str(new_gold)})
            return f"""🎉 成功购买地块！
位置: {block['name']}
类型: {block['type']}
花费: {price} 金币
当前金币: {new_gold}"""
        else:
            return "购买失败，请稍后再试"

    def upgrade_property(self, user_id):
        """升级当前位置的地块"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        # 获取玩家当前位置
        current_position = int(getattr(player, 'position', 0))
        
        # 检查是否是玩家的地产
        property_data = self.monopoly.properties_data.get(str(current_position))
        if not property_data or property_data.get('owner') != user_id:
            return "这不是您的地产"
            
        # 检查是否达到最高等级
        current_level = property_data.get('level', 1)
        if current_level >= 3:
            return "地产已达到最高等级"
            
        # 计算升级费用
        base_price = property_data.get('price', 500)
        upgrade_cost = int(base_price * 0.5 * current_level)
        
        # 检查玩家金币是否足够
        if int(player.gold) < upgrade_cost:
            return f"升级需要 {upgrade_cost} 金币，您的金币不足"
            
        # 扣除金币并升级地产
        new_gold = int(player.gold) - upgrade_cost
        if self.monopoly.upgrade_property(current_position):
            self._update_player_data(user_id, {'gold': str(new_gold)})
            return f"""🏗️ 地产升级成功！
位置: {current_position}
当前等级: {current_level + 1}
花费: {upgrade_cost} 金币
当前金币: {new_gold}"""
        else:
            return "升级失败，请稍后再试"

    def show_properties(self, user_id):
        """显示玩家的地产"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        properties = self.monopoly.get_player_properties(user_id)
        if not properties:
            return "您还没有购买任何地产"
            
        result = ["您的地产列表："]
        for pos in properties:
            prop_info = self.monopoly.get_property_info(pos)
            if prop_info:
                result.append(f"\n{prop_info['name']} ({prop_info['region']})")
                result.append(f"等级: {prop_info['level']}")
                result.append(f"价值: {prop_info['price']} 金币")
                result.append(f"当前租金: {prop_info['rent']} 金币")
                
        return "\n".join(result)

    def show_map(self, user_id):
        """显示地图状态"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册游戏"
            
        # 获取玩家当前位置
        current_position = int(getattr(player, 'position', 0))
        
        # 获取地图总格子数
        total_blocks = self.monopoly.map_data["total_blocks"]
        
        result = ["🗺️ 大富翁地图"]
        result.append("————————————")
        
        # 生成地图显示
        for pos in range(total_blocks):
            block = self.monopoly.get_block_info(pos)
            owner = self.monopoly.get_property_owner(pos)
            
            # 获取地块显示符号
            if pos == current_position:
                symbol = "👤"  # 玩家当前位置
            elif block['type'] == '起点':
                symbol = "🏁"
            elif owner:
                # 如果有主人，显示房屋等级
                level = self.monopoly.properties_data[str(pos)].get('level', 1)
                symbols = ["🏠", "🏘️", "🏰"]  # 不同等级的显示
                symbol = symbols[level - 1]
            else:
                # 根据地块类型显示不同符号
                type_symbols = {
                    "直辖市": "🌆",
                    "省会": "🏢",
                    "地级市": "🏣",
                    "县城": "🏘️",
                    "乡村": "🏡",
                    "空地": "⬜"
                }
                symbol = type_symbols.get(block['type'], "⬜")
                
            # 添加地块信息
            block_info = f"{symbol} {pos}:{block['name']}"
            if owner:
                owner_player = self.get_player(owner)
                owner_name = owner_player.nickname if owner_player else owner
                block_info += f"({owner_name})"
                
            if pos == current_position:
                block_info += " ← 当前位置"
                
            result.append(block_info)
            
            # 每5个地块换行
            if (pos + 1) % 5 == 0:
                result.append("————————————")
                
        return "\n".join(result)
