#!/usr/bin/env python3
"""临时测试脚本：验证当前配置实际返回的节点数"""

import json
from monitor import call_17ce_api, load_config
from city_nodes_config import get_node_config

def test_node_count():
    """测试实际返回的节点数"""
    print("=" * 60)
    print("🔬 测试当前配置实际返回的节点数")
    print("=" * 60)

    # 加载配置
    config = load_config()
    node_config = get_node_config()

    print(f"\n📋 当前节点配置：")
    print(json.dumps(node_config, indent=2, ensure_ascii=False))

    # 测试URL
    test_url = "https://www.baidu.com"
    print(f"\n🌐 测试URL: {test_url}")
    print("\n⏳ 正在调用17CE API...")

    # 调用API
    results = call_17ce_api(test_url, config)

    if results is None:
        print("\n❌ API调用失败")
        return

    # 分析结果
    data = results.get("data", [])
    node_count = len(data)

    print(f"\n" + "=" * 60)
    print(f"✅ 测试完成！")
    print(f"📊 实际返回节点数: {node_count} 个")
    print("=" * 60)

    if node_count > 0:
        print(f"\n📍 前5个节点详情：")
        for i, node in enumerate(data[:5], 1):
            node_info = node.get("NodeInfo", {}) or {}
            srcip_info = node.get("srcip", {}) or {}

            node_id = node_info.get("id", "未知")
            isp = node_info.get("isp", "未知")
            region = srcip_info.get("srcip_from", "未知")

            print(f"  {i}. NodeID: {node_id}, ISP: {isp}, 地区: {region}")

    # 理论计算
    theory_count = (
        len(node_config.get("pro_ids", [])) *
        len(node_config.get("isps", [])) *
        len(node_config.get("nodetype", [])) *
        node_config.get("num", 1)
    )
    print(f"\n📐 理论节点数: {theory_count} 个")
    print(f"   计算: {len(node_config.get('pro_ids', []))}省 × "
          f"{len(node_config.get('isps', []))}运营商 × "
          f"{len(node_config.get('nodetype', []))}类型 × "
          f"num={node_config.get('num', 1)}")

    if node_count > theory_count:
        print(f"\n⚠️  实际节点数({node_count}) > 理论值({theory_count})")
        print(f"   差值: {node_count - theory_count} 个")
        print(f"   说明: API返回的节点数超过预期，可能是17CE的分配策略导致")
    elif node_count < theory_count:
        print(f"\n✅ 实际节点数({node_count}) < 理论值({theory_count})")
        print(f"   差值: {theory_count - node_count} 个")
    else:
        print(f"\n✅ 实际节点数 = 理论值")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_node_count()
