
import os
import math
import sys

# 右手食指基部数据
COL_HAND_R_X = 409
COL_HAND_R_Y = 410
COL_HAND_R_Z = 411
COL_HAND_R_VX = 413
COL_HAND_R_VY = 414
COL_HAND_R_VZ = 415
COL_HAND_R_V = 416
COL_TIME = 0

def load_data(filepath):
    """加载数据"""
    data = []
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []
        
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[2:]:
            parts = line.strip().split('\t')
            if len(parts) > 420:
                try:
                    values = [float(x) if x else 0.0 for x in parts]
                    if values[0] > 0:
                        data.append(values)
                except ValueError:
                    continue
    return data

def search_around_time(data, target_time, window_size=0.3):
    """在目标时间点附近搜索更合理的出手点"""
    # 找到最接近的时间点索引
    start_idx = -1
    for i, row in enumerate(data):
        if row[COL_TIME] >= target_time - window_size:
            start_idx = i
            break
            
    if start_idx == -1: return []
    
    candidates = []
    
    for i in range(start_idx, len(data)):
        row = data[i]
        t = row[COL_TIME]
        if t > target_time + window_size: break
        
        # 提取数据
        z = row[COL_HAND_R_Z]
        vx = row[COL_HAND_R_VX]
        vy = row[COL_HAND_R_VY]
        vz = row[COL_HAND_R_VZ]
        
        # 计算指标
        speed = math.sqrt(vx**2 + vy**2 + vz**2)
        v_horiz = math.sqrt(vx**2 + vy**2)
        angle = math.degrees(math.atan2(vz, v_horiz)) if v_horiz > 0 else 0
        
        # 预估距离
        g = 9.81
        dist = 0
        if speed > 0 and angle > 0:
            rad = math.radians(angle)
            cos_a = math.cos(rad)
            sin_a = math.sin(rad)
            term1 = (speed**2 * cos_a) / g
            term2 = sin_a + math.sqrt(sin_a**2 + 2 * g * z / speed**2)
            dist = term1 * term2
            
        candidates.append({
            'idx': i,
            'time': t,
            'height': z,
            'speed': speed,
            'angle': angle,
            'distance': dist,
            'vz': vz
        })
        
    return candidates

def find_best_candidates(candidates):
    """筛选最佳候选点"""
    # 过滤掉角度为负或过小的点
    valid = [c for c in candidates if c['angle'] > 20 and c['angle'] < 50 and c['height'] > 1.6]
    
    # 如果没有完美的点，放宽条件
    if not valid:
        valid = [c for c in candidates if c['angle'] > 10 and c['height'] > 1.6]
        
    # 如果还是没有，只要求 vz > 0
    if not valid:
        valid = [c for c in candidates if c['vz'] > 0 and c['height'] > 1.6]
        
    # 按预估距离排序
    valid.sort(key=lambda x: x['distance'], reverse=True)
    
    # 返回前3个最佳点，以及原始目标时间点最近的点
    return valid[:5]

def main():
    base_dir = '/Users/jiahongxiang/shotput_report_demo'
    
    # 专注于 3.txt (3.15s) 和 4.txt (2.96s) 附近的数据
    tasks = [
        {'file': '3.txt', 'time': 3.15},
        {'file': '4.txt', 'time': 2.96}
    ]
    
    print(f"{'Time (s)':<10} | {'Height (m)':<10} | {'Speed (m/s)':<12} | {'Angle (deg)':<12} | {'Est. Dist (m)':<14} | {'Vertical V (m/s)'}")
    print("-" * 90)
    
    for task in tasks:
        fname = task['file']
        target_t = task['time']
        fpath = os.path.join(base_dir, fname)
        
        data = load_data(fpath)
        if not data: continue
        
        # 搜索范围：前后 0.15 秒
        candidates = search_around_time(data, target_t, 0.15)
        
        # 按时间排序
        candidates.sort(key=lambda x: x['time'])
        
        for c in candidates:
            # 标记用户指定的时刻
            marker = " <--" if abs(c['time'] - target_t) < 0.005 else ""
            
            # 高亮理想角度范围 (30-45度)
            angle_str = f"{c['angle']:.1f}"
            if 30 <= c['angle'] <= 45:
                angle_str += " *"
                
            print(f"{c['time']:<10.3f} | {c['height']:<10.2f} | {c['speed']:<12.2f} | {angle_str:<12} | {c['distance']:<14.2f} | {c['vz']:<10.2f}{marker}")

if __name__ == '__main__':
    main()
