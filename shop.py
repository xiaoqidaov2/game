import json
from common.log import logger
import csv
from collections import Counter

class Shop:
    def __init__(self, game):
        self.game = game
        
    def sell_item(self, user_id, content):
        """出售物品功能"""
        # 检查玩家是否存在
        player = self.game.get_player(user_id)
        if not player:
            return "您还没注册,请先注册"
            
        # 批量出售
        if content.startswith("批量出售"):
            inventory = player.inventory
            if not inventory:
                return "背包是空的,没有可以出售的物品"
                
            items = self.game.item_system.get_all_items()
            total_gold = 0
            sold_items = {}
            new_inventory = inventory.copy()
            
            # 获取当前装备
            equipped_weapon = player.equipped_weapon
            equipped_armor = player.equipped_armor
            
            # 解析要出售的物品类型
            parts = content.split()
            target_type = parts[1] if len(parts) > 1 else None
            
            # 中文类型映射
            type_mapping = {
                '武器': 'weapon',
                '护甲': 'armor',
                '消耗品': 'consumable',
                '鱼竿': 'fishing_rod',
                '鱼': 'fish'
            }
            
            # 将中文类型转换为系统类型
            system_type = type_mapping.get(target_type) if target_type else None
            
            # 统计每种物品的数量并计算总价值
            item_counts = Counter(inventory)
            
            for item_name, count in item_counts.items():
                if item_name in items:
                    # 如果指定了物品类型,则只出售该类型
                    if target_type:
                        item_type = items[item_name].get('type')
                        if item_type != system_type:
                            continue
                    
                    # 计算可出售数量（排除装备的物品）
                    sellable_count = count
                    if item_name == equipped_weapon or item_name == equipped_armor:
                        sellable_count -= 1
                        
                    if sellable_count > 0:
                        sold_items[item_name] = sellable_count
                        sell_price = int(float(items[item_name].get('price', 0)) * 0.6)
                        total_gold += sell_price * sellable_count
                        
                        # 从背包中移除指定数量的物品
                        for _ in range(sellable_count):
                            new_inventory.remove(item_name)
                        
            if not sold_items:
                if target_type:
                    return f"没有可以出售的{target_type}"
                return "没有可以出售的物品"
                
            # 更新玩家数据
            player.gold = player.gold + total_gold
            player.inventory = new_inventory
            
            # 保存更新后的玩家数据
            player.save_player_data(self.game.player_file, self.game.STANDARD_FIELDS)
            
            # 生成出售报告
            report = "批量出售成功:\n"
            for item_name, amount in sold_items.items():
                report += f"{item_name} x{amount}\n"
            report += f"共获得 {total_gold} 金币"
            return report
            
        # 单个出售
        elif content.startswith("出售"):
            try:
                parts = content.split()
                item_name = parts[1]
                amount = int(parts[2]) if len(parts) > 2 else 1
            except (IndexError, ValueError):
                return "出售格式错误！请使用: 出售 物品名 [数量]"
            
            # 获取商店物品信息
            items = self.game.item_system.get_all_items()
            if item_name not in items:
                return "商店中没有这个物品"
            
            # 获取背包中的物品数量
            inventory = player.inventory
            total_count = inventory.count(item_name)
            
            # 检查是否是装备中的物品
            equipped_count = 0
            if item_name == player.equipped_weapon or item_name == player.equipped_armor:
                equipped_count = 1
                
            # 计算可出售数量
            sellable_count = total_count - equipped_count
            
            if sellable_count < amount:
                if equipped_count > 0:
                    return f"背包中只有 {sellable_count} 个未装备的 {item_name}，无法出售 {amount} 个"
                else:
                    return f"背包中只有 {sellable_count} 个 {item_name}"
                
            # 计算出售价格（原价的60%）
            original_price = float(items[item_name].get('price', 0))
            sell_price = int(original_price * 0.6)
            total_sell_price = sell_price * amount
            
            # 更新背包和金币
            new_inventory = inventory.copy()
            for _ in range(amount):
                new_inventory.remove(item_name)
                
            player.gold = player.gold + total_sell_price
            player.inventory = new_inventory
            
            # 保存更新后的玩家数据
            player.save_player_data(self.game.player_file, self.game.STANDARD_FIELDS)
            
            return f"成功出售 {amount} 个 {item_name}，获得 {total_sell_price} 金币"
            
        return "无效的出售命令"

    def buy_item(self, user_id, content):
        """购买物品功能"""
        parts = content.split()
        if len(parts) < 2:
            return "请指定要购买的物品名称"
            
        item_name = parts[1]
        # 获取购买数量,默认为1
        amount = 1
        if len(parts) > 2:
            try:
                amount = int(parts[2])
                if amount <= 0:
                    return "购买数量必须大于0"
            except ValueError:
                return "购买数量必须是正整数"
            
        # 获取物品信息
        items = self.game.item_system.get_all_items()
        if item_name not in items:
            return "商店里没有这个物品"
            
        # 获取玩家信息
        player = self.game.get_player(user_id)
        if not player:
            return "您还没注册..."
            
        # 计算总价
        price = int(items[item_name].get('price', 0))
        total_price = price * amount
        
        # 检查金币是否足够
        if player.gold < total_price:
            return f"金币不足！需要 {total_price} 金币"
            
        # 更新玩家金币和背包
        player.gold -= total_price
        inventory = player.inventory
        for _ in range(amount):
            inventory.append(item_name)
        player.inventory = inventory
        
        # 保存更新后的玩家数据
        player.save_player_data(self.game.player_file, self.game.STANDARD_FIELDS)
        
        # 提示装备类型物品可以装备
        item_type = items[item_name].get('type')
        equip_hint = ""
        if item_type in ['weapon', 'armor']:
            equip_type = "武器" if item_type == 'weapon' else "护甲"
            equip_hint = f"\n💡 可以使用「装备 {item_name}」来装备此{equip_type}"
        
        return f"购买成功 {amount} 个 {item_name}, 剩余金币: {player.gold}{equip_hint}"

    def show_shop(self, content=""):
        """显示商店物品列表"""
        # 获取页码,默认第一页
        page = 1
        parts = content.split()
        if len(parts) > 1:
            try:
                page = int(parts[1])
                if page < 1:
                    page = 1
            except:
                page = 1
                
        items = self.game.get_shop_items()
        item_list = list(items.items())
        
        # 分页处理
        items_per_page = 10
        total_pages = (len(item_list) + items_per_page - 1) // items_per_page
        if page > total_pages:
            page = total_pages
            
        start = (page - 1) * items_per_page
        end = start + items_per_page
        current_items = item_list[start:end]

        shop_list = f"📦 商店物品列表 (第{page}/{total_pages}页)\n"
        shop_list += "━━━━━━━━━━━━━━━\n\n"
        
        for item_name, details in current_items:
            stats = []
            # 将字符串转换为整数进行比较
            if int(details.get('hp', '0')) > 0:
                stats.append(f"❤️生命+{details['hp']}")
            if int(details.get('attack', '0')) > 0:
                stats.append(f"⚔️攻击+{details['attack']}")
            if int(details.get('defense', '0')) > 0:
                stats.append(f"🛡防御+{details['defense']}")
            
            stats_str = f"\n└─ {' '.join(stats)}" if stats else ""
            shop_list += f"🔸 {item_name}\n"
            shop_list += f"└─ 💰{details.get('price', '0')}金币\n"
            shop_list += f"└─ 📝{details.get('desc', '')}{stats_str}\n\n"
            
        shop_list += "━━━━━━━━━━━━━━━\n"
        shop_list += "💡 输入 商店 [页码] 查看其他页"
        
        return shop_list 