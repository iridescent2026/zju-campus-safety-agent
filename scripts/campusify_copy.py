# -*- coding: utf-8 -*-
"""把前端与后端展示文案从「工厂/厂区/车间」迁移到「校园/校区/楼宇」。
只替换中文展示文案，不触碰英文标识符、CSS 类名与变量名。
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

# 长词优先，避免被短词拆碎
MAP = [
    ('工安智瞳 · 工厂数字孪生空间视图', '工安智瞳 · 校园安全数字孪生空间视图'),
    ('工安智瞳 · 工厂安全首页', '工安智瞳 · 校园安全首页'),
    ('工安智瞳 · 工业安全协同工作台', '工安智瞳 · 校园安全协同工作台'),
    ('工安智瞳 · 遥感与工厂空间', '工安智瞳 · 遥感与校园空间'),
    ('工厂安全数字孪生', '校园安全数字孪生'),
    ('工厂数字孪生', '校园安全数字孪生'),
    ('工业安全协同工作台', '校园安全协同工作台'),
    ('工厂安全首页', '校园安全首页'),
    ('遥感与工厂空间', '遥感与校园空间'),
    ('工厂场景设计示意', '校园场景设计示意'),
    ('工厂场景设计', '校园场景设计'),
    ('工厂场景-', '校园场景-'),
    ('工厂全景总视图', '校园全景总视图'),
    ('工厂交互三维场景', '校园交互三维场景'),
    ('工厂后台', '校园后台'),
    ('工厂观测', '校园观测'),
    ('工厂版本', '校园版本'),
    ('工厂分析', '校园分析'),
    ('工厂视图', '校园视图'),
    ('自动化装配车间', '教学实验楼'),
    ('综合动力设备工区', '后勤保障中心'),
    ('地下动力室', '后勤能源站'),
    ('A 区 · 自动化装配车间', 'A 区 · 教学实验楼'),
    ('B 区 · 地下动力室', 'B 区 · 后勤能源站'),
    ('A 装配 / B 动力', 'A 教学 / B 后勤'),
    ('A · 自动化装配', 'A · 教学实验'),
    ('B · 动力设备', 'B · 后勤保障'),
    ('装配制造 · 西侧厂房', '教学实验 · 西侧楼宇'),
    ('动力设备 · 东侧厂房与控制侧翼', '后勤保障 · 东侧楼宇与控制侧翼'),
    ('厂区整体剖面', '校区整体剖面'),
    ('厂区三维外观', '校区三维外观'),
    ('厂区储罐组', '燃气调压储罐组'),
    ('厂区轮廓', '校区轮廓'),
    ('厂区信息', '校区信息'),
    ('厂区平面', '校区平面'),
    ('厂区', '校区'),
    ('装配制造', '教学实验'),
    ('动力设备', '后勤保障'),
    ('车间低压配电箱', '实验楼低压配电箱'),
    ('车间桥式起重机', '实验楼桥式起重机'),
    ('工厂', '校园'),
    ('工区', '区域'),
    ('车间', '实验楼'),
    ('厂房', '楼宇'),
]

TARGETS = []
for pattern in ('frontend/*.html', 'frontend/*.mjs', 'frontend/*.js', 'gis/*.py'):
    TARGETS.extend(ROOT.glob(pattern))

report = []
for path in TARGETS:
    try:
        original = path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        continue
    text = original
    count = 0
    for old, new in MAP:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
            count += n
    if count:
        path.write_text(text, encoding='utf-8')
        report.append((path.relative_to(ROOT).as_posix(), count))

for name, n in sorted(report, key=lambda x: -x[1]):
    print(f'{n:4d}  {name}')
print(f'---\n{len(report)} files, {sum(n for _, n in report)} replacements')
