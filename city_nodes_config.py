#!/usr/bin/env python3
# 全国主要城市节点配置 - 基于用户提供的城市表
# 每个城市配置2个节点: IDC + 路由器

# 格式: {"name": "城市名", "pro_id": 省份ID, "city_id": 城市ID}
MAJOR_CITIES = [
    # 直辖市
    {"name": "北京", "pro_id": 180, "city_id": 202},
    {"name": "上海", "pro_id": 221, "city_id": 280},
    {"name": "重庆", "pro_id": 49, "city_id": 246},
    {"name": "天津", "pro_id": 243, "city_id": 279},

    # 东部沿海重点城市
    {"name": "深圳", "pro_id": 195, "city_id": 264},
    {"name": "广州", "pro_id": 195, "city_id": 217},
    {"name": "杭州", "pro_id": 355, "city_id": 573},
    {"name": "南京", "pro_id": 357, "city_id": 590},
    {"name": "青岛", "pro_id": 190, "city_id": 516},
    {"name": "厦门", "pro_id": 79, "city_id": 476},

    # 华中地区
    {"name": "武汉", "pro_id": 235, "city_id": 259},
    {"name": "郑州", "pro_id": 196, "city_id": 271},
    {"name": "长沙", "pro_id": 350, "city_id": 461},
    {"name": "南昌", "pro_id": 239, "city_id": 275},

    # 西部地区
    {"name": "成都", "pro_id": 353, "city_id": 539},
    {"name": "西安", "pro_id": 194, "city_id": 601},
    {"name": "昆明", "pro_id": 227, "city_id": 560},
    {"name": "贵阳", "pro_id": 188, "city_id": 392},

    # 北部地区
    {"name": "沈阳", "pro_id": 349, "city_id": 582},
    {"name": "大连", "pro_id": 349, "city_id": 443},
    {"name": "哈尔滨", "pro_id": 192, "city_id": 584},
    {"name": "长春", "pro_id": 351, "city_id": 587},

    # 其他省会
    {"name": "济南", "pro_id": 190, "city_id": 212},
    {"name": "石家庄", "pro_id": 250, "city_id": 293},
    {"name": "太原", "pro_id": 193, "city_id": 667},
    {"name": "合肥", "pro_id": 236, "city_id": 609},
    {"name": "福州", "pro_id": 79, "city_id": 471},
    {"name": "南宁", "pro_id": 352, "city_id": 532},

    # 西北地区
    {"name": "兰州", "pro_id": 80, "city_id": 602},
    {"name": "西宁", "pro_id": 356, "city_id": 574},
    {"name": "银川", "pro_id": 189, "city_id": 575},
    {"name": "乌鲁木齐", "pro_id": 346, "city_id": 719},
    {"name": "呼和浩特", "pro_id": 183, "city_id": 433},
]

def get_province_ids():
    """获取去重后的省份ID列表"""
    return sorted(set(city["pro_id"] for city in MAJOR_CITIES))

def get_city_ids():
    """获取城市ID列表"""
    return [city["city_id"] for city in MAJOR_CITIES]

def get_pro_ids():
    """获取省份ID列表（去重）"""
    return list(set([city["pro_id"] for city in MAJOR_CITIES]))

def get_node_config():
    """生成17CE API节点配置（返回数组格式，符合官方API要求）

    最小化配置：4个核心省份，严格控制积分消耗
    - 北京(180)、上海(221)、广东(195)、浙江(355)
    - 覆盖华北、华东、华南最重要的经济区

    参数说明：
    - pro_ids: 省份ID数组（官方API参数，4个核心省份）
    - num: 每个省份分配节点数（设为1最省积分）
    - nodetype: [1, 2] 表示 IDC + 路由器
    - isps: [1, 2, 7] 表示 电信 + 联通 + 移动
    - areas: [1] 表示中国大陆

    注意：city_ids 不是官方API参数，已移除
    """
    # 4个最核心省份：北京、上海、广东、浙江
    core_provinces = [180, 221, 195, 355]

    return {
        "pro_ids": core_provinces,  # 4个核心省份
        "num": 1,                    # 每省1个节点，严格控制积分
        "nodetype": [1, 2],          # 1=IDC, 2=路由器
        "isps": [1, 2, 7],           # 1=电信, 2=联通, 7=移动
        "areas": [1]                 # 1=中国大陆
    }

if __name__ == "__main__":
    print(f"🏙️ 配置城市总数: {len(MAJOR_CITIES)}")
    print(f"📍 省份数量: {len(get_province_ids())}")
    print(f"🔢 节点总数: {len(MAJOR_CITIES) * 2}")
    print(f"\n📊 节点配置:")
    config = get_node_config()
    for key, value in config.items():
        print(f"  {key}: {value}")
