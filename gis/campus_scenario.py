"""Design context for the campus demonstration, never a verified service map."""
import copy

_DRAINAGE = {
    'scenarioId': 'CAMPUS-DRAIN-B05',
    'status': 'design_assumption',
    'service': '工程训练中心与后勤楼的排水保障核查',
    'hypothesis': '若该泵组承担示意楼宇的排水且备用能力不足，需核查排水保障及实验场地使用安排；这不是已发生积水、停课或设备故障的结论',
    'verification': '核对实际服务范围、备用泵可用性、排水管路与隔离状态，以及场地积水和现场负责人记录；供电柜属于候选供电关联，不代表泵故障会损坏电柜',
    'roles': ['校园安全员', '后勤维修员', '实验室管理岗位', '独立复核员'],
    'dataBoundary': '设计场景，不是浙江大学实际设施或业务系统接入证明',
}


def service_context(entity_id):
    # Never attach the pump's service assumptions to an unrelated asset.
    return copy.deepcopy(_DRAINAGE) if entity_id == 'B-05' else None
