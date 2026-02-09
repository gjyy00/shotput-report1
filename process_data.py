#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
铁饼动捕数据处理脚本
提取铁饼轨迹和身体重心数据，计算速度等生物力学指标
"""

import json
import os
import math

# 列索引定义（从0开始）
# 每个标记点有12列：X, Y, Z, 长度, v(X), v(Y), v(Z), v(绝对值), a(X), a(Y), a(Z), a(绝对值)
COL_TIME = 0

# 重心数据
COL_COG_X = 1
COL_COG_Y = 2
COL_COG_Z = 3
COL_COG_VX = 5
COL_COG_VY = 6
COL_COG_VZ = 7
COL_COG_V = 8

# 右手腕数据 (作为铁饼位置的近似)
COL_WRIST_R_X = 145  # 列146，索引145
COL_WRIST_R_Y = 146
COL_WRIST_R_Z = 147
COL_WRIST_R_VX = 149
COL_WRIST_R_VY = 150
COL_WRIST_R_VZ = 151
COL_WRIST_R_V = 152

# 右手食指基部数据 (更接近铁饼释放点)
COL_HAND_R_X = 409  # 列410，索引409
COL_HAND_R_Y = 410
COL_HAND_R_Z = 411
COL_HAND_R_VX = 413
COL_HAND_R_VY = 414
COL_HAND_R_VZ = 415
COL_HAND_R_V = 416

# 骨架关节点列索引 (0-based)
SKELETON_JOINTS = {
    'root': 13,
    'pelvis': 97,
    'spine_low': 217,
    'spine_high': 229,
    'torso': 109,
    'neck': 193,
    'head': 205,  # skullbase
    'clavicle_r': 241,
    'shoulder_r': 121,
    'elbow_r': 133,
    'wrist_r': 145,
    'hand_index_r': 409,   # 右手食指基部 /Feature/Hand/Index/Base/Right
    'hand_little_r': 421,  # 右手小指基部 /Feature/Hand/Little/Base/Right
    'clavicle_l': 253,
    'shoulder_l': 157,
    'elbow_l': 169,
    'wrist_l': 181,
    'hand_index_l': 349,   # 左手食指基部 /Feature/Hand/Index/Base/Left
    'hand_little_l': 361,  # 左手小指基部 /Feature/Hand/Little/Base/Left
    'hip_r': 25,
    'knee_r': 37,
    'ankle_r': 49,
    'foot_r': 265,  # midfoot
    'hip_l': 61,
    'knee_l': 73,
    'ankle_l': 85,
    'foot_l': 277,  # midfoot
}

# rotation.txt 中的关节列索引 (0-based, X列)
# rotation.txt 有不同的列结构，每个关节有12列
ROTATION_JOINTS = {
    'root': 1,
    'hip_r': 13,
    'knee_r': 25,
    'ankle_r': 37,
    'hip_l': 49,
    'knee_l': 61,
    'ankle_l': 73,
    'pelvis': 85,
    'torso': 97,
    'shoulder_r': 109,
    'elbow_r': 121,
    'wrist_r': 133,
    'shoulder_l': 145,
    'elbow_l': 157,
    'wrist_l': 169,
    'neck': 181,
    'head': 193,  # skullbase
    'spine_low': 205,
    'spine_high': 217,
    'clavicle_r': 229,
    'clavicle_l': 241,
    'foot_r': 253,  # midfoot
    'foot_l': 265,  # midfoot
}

# 骨架连接定义 (骨骼)
SKELETON_BONES = [
    # 躯干
    ('pelvis', 'spine_low'),
    ('spine_low', 'spine_high'),
    ('spine_high', 'torso'),
    ('torso', 'neck'),
    ('neck', 'head'),
    # 右臂
    ('torso', 'clavicle_r'),
    ('clavicle_r', 'shoulder_r'),
    ('shoulder_r', 'elbow_r'),
    ('elbow_r', 'wrist_r'),
    ('wrist_r', 'hand_index_r'),   # 手腕到食指基部
    ('wrist_r', 'hand_little_r'),  # 手腕到小指基部
    ('hand_index_r', 'hand_little_r'),  # 食指到小指（手掌）
    # 左臂
    ('torso', 'clavicle_l'),
    ('clavicle_l', 'shoulder_l'),
    ('shoulder_l', 'elbow_l'),
    ('elbow_l', 'wrist_l'),
    ('wrist_l', 'hand_index_l'),   # 手腕到食指基部
    ('wrist_l', 'hand_little_l'),  # 手腕到小指基部
    ('hand_index_l', 'hand_little_l'),  # 食指到小指（手掌）
    # 右腿
    ('pelvis', 'hip_r'),
    ('hip_r', 'knee_r'),
    ('knee_r', 'ankle_r'),
    ('ankle_r', 'foot_r'),
    # 左腿
    ('pelvis', 'hip_l'),
    ('hip_l', 'knee_l'),
    ('knee_l', 'ankle_l'),
    ('ankle_l', 'foot_l'),
]

def load_data(filepath):
    """加载动捕数据文件，跳过标题行"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # 跳过前两行（标题和参数行）
        for line in lines[2:]:
            parts = line.strip().split('\t')
            if len(parts) > 100:
                try:
                    values = [float(x) if x else 0.0 for x in parts]
                    if values[0] > 0:  # 有效时间戳
                        data.append(values)
                except ValueError:
                    continue
    return data

def load_rotation_data(filepath):
    """加载旋转数据文件，跳过标题行"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # 跳过前两行（标题和参数行）
        for line in lines[2:]:
            parts = line.strip().split('\t')
            if len(parts) > 50:  # rotation.txt 列数较少
                try:
                    values = [float(x) if x else 0.0 for x in parts]
                    if values[0] > 0:  # 有效时间戳
                        data.append(values)
                except ValueError:
                    continue
    return data

def vector_norm(v):
    """计算向量长度"""
    return math.sqrt(sum(x*x for x in v))

def extract_discus_trajectory(data):
    """
    提取铁饼轨迹数据（使用右手数据）
    """
    times = []
    positions = []
    velocities = []
    speeds = []
    
    for row in data:
        t = row[COL_TIME]
        # 使用右手食指基部作为铁饼位置
        x = row[COL_HAND_R_X]
        y = row[COL_HAND_R_Y]
        z = row[COL_HAND_R_Z]
        vx = row[COL_HAND_R_VX]
        vy = row[COL_HAND_R_VY]
        vz = row[COL_HAND_R_VZ]
        v = row[COL_HAND_R_V]
        
        # 跳过位置为零或接近原点的无效数据
        if abs(x) < 0.01 and abs(y) < 0.01 and abs(z) < 0.01:
            continue
        
        times.append(t)
        positions.append([x, y, z])
        velocities.append([vx, vy, vz])
        speeds.append(v)
    
    return {
        'times': times,
        'positions': positions,
        'velocities': velocities,
        'speeds': speeds
    }

def extract_com_trajectory(data):
    """
    提取身体重心轨迹
    """
    times = []
    positions = []
    speeds = []
    
    for row in data:
        t = row[COL_TIME]
        x = row[COL_COG_X]
        y = row[COL_COG_Y]
        z = row[COL_COG_Z]
        v = row[COL_COG_V]
        
        times.append(t)
        positions.append([x, y, z])
        speeds.append(v)
    
    return {
        'times': times,
        'positions': positions,
        'speeds': speeds
    }

def extract_skeleton_data(data):
    """
    提取骨架关节点数据
    """
    frames = []
    
    for row in data:
        frame_joints = {}
        for joint_name, col_idx in SKELETON_JOINTS.items():
            try:
                x = row[col_idx]
                y = row[col_idx + 1]
                z = row[col_idx + 2]
                frame_joints[joint_name] = [x, y, z]
            except IndexError:
                frame_joints[joint_name] = [0, 0, 0]
        frames.append(frame_joints)
    
    return {
        'frames': frames,
        'bones': SKELETON_BONES,
        'joint_names': list(SKELETON_JOINTS.keys())
    }

def extract_rotation_data(rotation_data):
    """
    提取骨架关节旋转数据（欧拉角，弧度）
    """
    frames = []
    
    for row in rotation_data:
        frame_rotations = {}
        for joint_name, col_idx in ROTATION_JOINTS.items():
            try:
                rx = row[col_idx]      # X轴旋转（弧度）
                ry = row[col_idx + 1]  # Y轴旋转（弧度）
                rz = row[col_idx + 2]  # Z轴旋转（弧度）
                frame_rotations[joint_name] = [rx, ry, rz]
            except IndexError:
                frame_rotations[joint_name] = [0, 0, 0]
        frames.append(frame_rotations)
    
    return {
        'frames': frames,
        'joint_names': list(ROTATION_JOINTS.keys())
    }

def extract_joint_speeds(data):
    """
    提取各关节的速度数据
    每个关节的速度在其基础列索引+7的位置 (v绝对值)
    """
    joint_speeds = {}
    
    # 定义关节的中文名称映射
    joint_names_cn = {
        'root': '根节点',
        'pelvis': '骨盆',
        'spine_low': '下脊柱',
        'spine_high': '上脊柱',
        'torso': '躯干',
        'neck': '颈部',
        'head': '头部',
        'clavicle_r': '右锁骨',
        'shoulder_r': '右肩',
        'elbow_r': '右肘',
        'wrist_r': '右腕',
        'hand_index_r': '右手食指',
        'hand_little_r': '右手小指',
        'clavicle_l': '左锁骨',
        'shoulder_l': '左肩',
        'elbow_l': '左肘',
        'wrist_l': '左腕',
        'hand_index_l': '左手食指',
        'hand_little_l': '左手小指',
        'hip_r': '右髋',
        'knee_r': '右膝',
        'ankle_r': '右踝',
        'foot_r': '右脚',
        'hip_l': '左髋',
        'knee_l': '左膝',
        'ankle_l': '左踝',
        'foot_l': '左脚',
    }
    
    for joint_name, col_idx in SKELETON_JOINTS.items():
        speeds = []
        speed_col = col_idx + 7  # v(绝对值) 在基础索引+7的位置
        
        for row in data:
            try:
                speed = row[speed_col]
                speeds.append(speed)
            except IndexError:
                speeds.append(0.0)
        
        joint_speeds[joint_name] = {
            'speeds': speeds,
            'name_cn': joint_names_cn.get(joint_name, joint_name),
            'max_speed': max(speeds) if speeds else 0,
            'avg_speed': sum(speeds) / len(speeds) if speeds else 0
        }
    
    return joint_speeds

def calculate_angle(p1, p2, p3):
    """
    计算三点形成的角度 (p1-p2-p3)，p2为顶点
    返回角度（度），180度表示完全伸直
    """
    # 向量 v1: p2 -> p1 (大臂，指向肩)
    v1 = [p1[0]-p2[0], p1[1]-p2[1], p1[2]-p2[2]]
    # 向量 v2: p2 -> p3 (小臂，指向腕)
    v2 = [p3[0]-p2[0], p3[1]-p2[1], p3[2]-p2[2]]
    
    # 计算点积
    dot_product = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
    
    # 计算模长
    norm1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
    norm2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
    
    if norm1 == 0 or norm2 == 0:
        return 0
    
    # 计算夹角余弦
    cos_angle = dot_product / (norm1 * norm2)
    # 限制范围 [-1, 1] 避免计算误差导致越界
    cos_angle = max(-1.0, min(1.0, cos_angle))
    
    # 计算弧度
    rad = math.acos(cos_angle)
    return math.degrees(rad)

def find_release_point(discus_data, skeleton_data=None):
    """
    找到铁饼/铅球释放点
    """
    speeds = discus_data['speeds']
    positions = discus_data['positions']
    times = discus_data['times']
    n = len(speeds)
    
    # 跳过开头的边界伪影帧
    skip_start = max(5, int(n * 0.10))
    skip_end = max(3, int(n * 0.02))
    search_end = n - skip_end
    
    # 在有效范围内找全局最大速度
    global_max_speed = 0
    for i in range(skip_start, search_end):
        if speeds[i] > global_max_speed:
            global_max_speed = speeds[i]
            
    # 智能判断项目类型
    is_shot_put = global_max_speed < 18.0
    min_release_height = 1.6 if is_shot_put else 1.2
    
    print(f"项目类型推断: {'铅球(Shot Put)' if is_shot_put else '铁饼(Discus)'}, 最大速度={global_max_speed:.2f}m/s, 最小高度阈值={min_release_height}m")
    
    # 平滑速度
    smoothed = []
    half_win = 2
    for i in range(n):
        start = max(0, i - half_win)
        end = min(n, i + half_win + 1)
        segment = speeds[start:end]
        smoothed.append(sum(segment) / len(segment))
        
    release_idx = -1
    
    # ====== 铅球专用逻辑：结合肘关节角度 ======
    if is_shot_put and skeleton_data:
        print("应用铅球优化算法：寻找肘关节伸直且速度较大的点...")
        candidates = []
        frames = skeleton_data['frames']
        
        # 确保帧数对齐
        n_frames = min(len(frames), n)
        
        for i in range(skip_start, min(search_end, n_frames)):
            # 获取关节坐标
            try:
                shoulder = frames[i]['shoulder_r']
                elbow = frames[i]['elbow_r']
                wrist = frames[i]['wrist_r']
                
                # 计算肘关节角度
                angle = calculate_angle(shoulder, elbow, wrist)
                height = positions[i][2]
                speed = speeds[i]
                
                # 筛选条件：高度达标，且肘关节接近伸直 (>130度)
                # 增加条件：垂直速度必须大于0 (出手角度必须为正)
                if height > 1.6 and angle > 130 and velocities[i][2] > 0:
                    candidates.append({
                        'idx': i,
                        'speed': speed,
                        'height': height,
                        'angle': angle,
                        'vz': velocities[i][2],
                        # 综合评分：速度 * (角度权重) * (垂直速度权重)
                        # 优先选择向上冲的时刻
                        'score': speed * (angle / 180.0)
                    })
            except (KeyError, IndexError):
                continue
                
        if candidates:
            # 选择综合评分最高的点，或者直接选速度最大的点
            # 这里选择在伸直阶段速度最大的点
            best = max(candidates, key=lambda x: x['speed'])
            release_idx = best['idx']
            print(f"铅球释放点锁定: 帧{release_idx}, 速度={best['speed']:.2f}m/s, 高度={best['height']:.2f}m, 角度={best['angle']:.1f}°")
            
            return {
                'index': release_idx,
                'position': positions[release_idx],
                'speed': speeds[release_idx],
                'time': times[release_idx]
            }
        else:
            print("未找到满足铅球条件的释放点，回退到通用逻辑")

    # ====== 通用/铁饼逻辑 ======
    # 找局部峰值
    peaks = []
    for i in range(skip_start + 1, search_end - 1):
        if smoothed[i] > smoothed[i-1] and smoothed[i] >= smoothed[i+1]:
            if positions[i][2] > min_release_height:
                peaks.append({'idx': i, 'speed': speeds[i], 'height': positions[i][2]})
                
    # 筛选显著峰值
    min_peak_speed = global_max_speed * 0.40
    
    for peak in peaks:
        if peak['speed'] < min_peak_speed:
            continue
            
        # 检查峰后下降
        look_ahead = min(peak['idx'] + 10, search_end)
        min_after = peak['speed']
        for j in range(peak['idx'] + 1, look_ahead):
            if smoothed[j] < min_after:
                min_after = smoothed[j]
        
        drop_ratio = (peak['speed'] - min_after) / peak['speed']
        if drop_ratio > 0.05:
            release_idx = peak['idx']
            print(f"释放点检测(局部峰值法): 帧{peak['idx']}, 速度={peak['speed']:.2f}m/s, 高度={peak['height']:.2f}m, 峰后下降{drop_ratio*100:.1f}%")
            break
            
    # 回退策略
    if release_idx == -1:
        best_idx = -1
        max_val = -1
        
        for i in range(skip_start, search_end):
            if positions[i][2] > min_release_height:
                if speeds[i] > max_val:
                    max_val = speeds[i]
                    best_idx = i
        
        if best_idx != -1:
            release_idx = best_idx
            print(f"释放点检测(高位最大速度法): 帧{best_idx}, 速度={max_val:.2f}m/s")
        else:
            # 保底
            max_speed_idx = skip_start
            for i in range(skip_start, search_end):
                if speeds[i] > speeds[max_speed_idx]:
                    max_speed_idx = i
            release_idx = max_speed_idx
            print(f"释放点检测(保底全局最大): 帧{release_idx}")
            
        # 微调
        range_val = 5
        refined_idx = release_idx
        current_max_speed = speeds[release_idx]
        
        for i in range(max(skip_start, release_idx - range_val), min(search_end, release_idx + range_val + 1)):
            if speeds[i] > current_max_speed and positions[i][2] > min_release_height - 0.1:
                refined_idx = i
                current_max_speed = speeds[i]
        release_idx = refined_idx

    return {
        'index': release_idx,
        'position': positions[release_idx],
        'speed': speeds[release_idx],
        'time': times[release_idx]
    }

def calculate_biomechanics(discus_data, com_data, release_point):
    """
    计算铁饼投掷的生物力学指标
    """
    positions = discus_data['positions']
    speeds = discus_data['speeds']
    velocities = discus_data['velocities']
    times = discus_data['times']
    
    release_idx = release_point['index']
    release_pos = release_point['position']
    release_vel = velocities[release_idx]
    release_speed = release_point['speed']
    
    # 1. 出手速度 (m/s)
    release_velocity = release_speed
    
    # 2. 出手高度 (m)
    release_height = release_pos[2]
    
    # 3. 出手角度 (度) - 相对于水平面
    horizontal_v = math.sqrt(release_vel[0]**2 + release_vel[1]**2)
    if horizontal_v > 0:
        release_angle = math.degrees(math.atan2(release_vel[2], horizontal_v))
    else:
        release_angle = 35.0
    
    # 4. 旋转圈数估计
    xy_positions = [p[:2] for p in positions[:release_idx]]
    if len(xy_positions) > 10:
        center_x = sum(p[0] for p in xy_positions) / len(xy_positions)
        center_y = sum(p[1] for p in xy_positions) / len(xy_positions)
        
        angles = []
        for p in xy_positions:
            angle = math.atan2(p[1] - center_y, p[0] - center_x)
            angles.append(angle)
        
        # 展开角度计算总旋转
        total_rotation = 0
        for i in range(1, len(angles)):
            diff = angles[i] - angles[i-1]
            while diff > math.pi:
                diff -= 2 * math.pi
            while diff < -math.pi:
                diff += 2 * math.pi
            total_rotation += abs(diff)
        
        rotation_count = total_rotation / (2 * math.pi)
    else:
        rotation_count = 1.5
    
    # 5. 最大速度
    max_speed = max(speeds)
    
    # 6. 动作时间
    total_time = times[release_idx] - times[0]
    
    # 7. 轨迹长度
    trajectory_length = 0
    for j in range(1, release_idx):
        diff = [positions[j][k] - positions[j-1][k] for k in range(3)]
        trajectory_length += vector_norm(diff)
    
    # 8. 水平出手方向（相对于投掷方向）
    horizontal_direction = math.degrees(math.atan2(release_vel[1], release_vel[0]))
    
    return {
        'release_velocity': round(release_velocity, 2),
        'release_height': round(release_height, 2),
        'release_angle': round(release_angle, 1),
        'rotation_count': round(rotation_count, 1),
        'max_speed': round(max_speed, 2),
        'total_time': round(total_time, 3),
        'trajectory_length': round(trajectory_length, 2),
        'release_position': [round(x, 2) for x in release_pos],
        'horizontal_direction': round(horizontal_direction, 1)
    }

# 阶段颜色定义
PHASE_COLORS = {
    'preparation': '#22c55e',   # 绿色 - 预备阶段
    'entry': '#3b82f6',         # 蓝色 - 进入旋转阶段
    'airborne': '#f97316',      # 橙色 - 腾空阶段
    'transition': '#8b5cf6',    # 紫色 - 过渡阶段
    'delivery': '#ef4444',      # 红色 - 最后用力阶段
}

def find_local_maxima(data, min_distance=10):
    """
    找到数据中的局部极大值点
    min_distance: 极大值点之间的最小距离
    """
    maxima = []
    n = len(data)
    
    i = min_distance
    while i < n - min_distance:
        is_max = True
        for j in range(i - min_distance, i + min_distance + 1):
            if j != i and data[j] >= data[i]:
                is_max = False
                break
        if is_max and data[i] > 0:
            maxima.append(i)
            i += min_distance
        else:
            i += 1
    
    return maxima

def auto_detect_phases(data, discus_data, skeleton_data, release_point, times):
    """
    自动检测铁饼投掷的5个技术阶段
    
    正确的阶段定义（基于专业铁饼投掷技术）：
    1. Preparation (预备阶段): 从预摆最大幅度 → 第一次右脚离地
    2. Entry (进入旋转阶段): 第一次右脚离地 → 第一次左脚离地
    3. Airborne (腾空阶段): 双脚都离地（左脚离地后） → 右脚落地
    4. Transition (过渡阶段): 右脚落地 → 左脚落地
    5. Delivery (最后用力阶段): 左脚落地 → 出手（释放点）
    """
    phases = []
    speeds = discus_data['speeds']
    discus_times = discus_data['times']
    discus_positions = discus_data['positions']
    release_idx = release_point['index']
    release_time = release_point['time']
    n_data = len(data)
    n_discus = len(speeds)
    
    # ============ 提取脚部高度数据 ============
    foot_r_heights = []  # 右脚（踝关节）高度
    foot_l_heights = []  # 左脚（踝关节）高度
    
    for row in data:
        foot_r_z = row[SKELETON_JOINTS['ankle_r'] + 2]  # Z坐标
        foot_l_z = row[SKELETON_JOINTS['ankle_l'] + 2]
        foot_r_heights.append(foot_r_z)
        foot_l_heights.append(foot_l_z)
    
    # 使用绝对阈值检测离地（经验证 0.15m 是合理的阈值）
    # 正常站立时踝关节高度约0.07-0.09m，超过0.15m明确表示离地
    TAKEOFF_THRESHOLD = 0.15
    
    # 索引转换函数
    def discus_to_data_idx(d_idx):
        return int(d_idx * n_data / n_discus) if n_discus > 0 else 0
    
    def data_to_discus_idx(data_idx):
        return int(data_idx * n_discus / n_data) if n_data > 0 else 0
    
    def safe_get_time(data_idx):
        idx = max(0, min(data_idx, n_data - 1))
        return times[idx]
    
    release_data_idx = discus_to_data_idx(release_idx)
    
    # ============ 1. 检测预摆最大幅度位置（Preparation开始点）============
    # 特征：右手在水平面上的旋转方向改变点（逆时针扭紧到最大后开始顺时针）
    # 使用角度变化来检测
    
    hand_positions = discus_positions  # 右手位置
    
    # 计算每帧右手相对于原点的角度
    angles = []
    for i in range(n_discus):
        hand_x, hand_y = hand_positions[i][0], hand_positions[i][1]
        angle = math.atan2(hand_y, hand_x)
        angles.append(math.degrees(angle))
    
    # 计算角度变化率
    angle_changes = []
    for i in range(1, len(angles)):
        diff = angles[i] - angles[i-1]
        # 处理角度跨越-180到180的情况
        while diff > 180:
            diff -= 360
        while diff < -180:
            diff += 360
        angle_changes.append(diff)
    
    # 找到预摆最大位置：角度变化从负变正的点
    # 在大约500-700帧范围内寻找
    search_start_idx = int(n_discus * 0.45)  # 约45%位置开始找
    search_end_idx = int(n_discus * 0.75)    # 到75%位置
    
    prep_start_idx = search_start_idx
    
    # 寻找角度变化从负变正的转折点
    for i in range(search_start_idx + 5, search_end_idx - 5):
        if i < len(angle_changes) - 5:
            # 检查前5帧平均变化和后5帧平均变化
            avg_before = sum(angle_changes[i-5:i]) / 5
            avg_after = sum(angle_changes[i:i+5]) / 5
            
            # 如果从负变正（预摆结束，开始顺时针旋转）
            if avg_before < -0.1 and avg_after > 0.1:
                prep_start_idx = i
                break
    
    # ============ 2. 检测第一次右脚离地（Preparation结束/Entry开始）============
    search_start = discus_to_data_idx(prep_start_idx)
    
    right_foot_off_idx = None
    for i in range(search_start, release_data_idx):
        if foot_r_heights[i] > TAKEOFF_THRESHOLD:
            right_foot_off_idx = i
            break
    
    if right_foot_off_idx is None:
        right_foot_off_idx = search_start + int((release_data_idx - search_start) * 0.2)
    
    # ============ 3. 检测第一次左脚离地（Entry结束/Airborne开始）============
    left_foot_off_idx = None
    for i in range(right_foot_off_idx, release_data_idx):
        if foot_l_heights[i] > TAKEOFF_THRESHOLD:
            left_foot_off_idx = i
            break
    
    if left_foot_off_idx is None:
        left_foot_off_idx = right_foot_off_idx + int((release_data_idx - right_foot_off_idx) * 0.3)
    
    # ============ 4. 检测右脚落地（Airborne结束/Transition开始）============
    # 右脚在离地后下降到阈值以下
    right_foot_land_idx = None
    for i in range(left_foot_off_idx, release_data_idx):
        if foot_r_heights[i] < TAKEOFF_THRESHOLD:
            right_foot_land_idx = i
            break
    
    if right_foot_land_idx is None:
        right_foot_land_idx = left_foot_off_idx + int((release_data_idx - left_foot_off_idx) * 0.3)
    
    # ============ 5. 检测左脚落地（Transition结束/Delivery开始）============
    left_foot_land_idx = None
    for i in range(right_foot_land_idx, release_data_idx):
        if foot_l_heights[i] < TAKEOFF_THRESHOLD:
            left_foot_land_idx = i
            break
    
    if left_foot_land_idx is None:
        left_foot_land_idx = right_foot_land_idx + int((release_data_idx - right_foot_land_idx) * 0.3)
    
    # ============ 6. 确保时间顺序正确 ============
    prep_start_data_idx = discus_to_data_idx(prep_start_idx)
    
    # 确保所有关键点按时间顺序排列
    prep_start_data_idx = max(0, min(prep_start_data_idx, release_data_idx - 50))
    right_foot_off_idx = max(prep_start_data_idx + 1, min(right_foot_off_idx, release_data_idx - 40))
    left_foot_off_idx = max(right_foot_off_idx + 1, min(left_foot_off_idx, release_data_idx - 30))
    right_foot_land_idx = max(left_foot_off_idx + 1, min(right_foot_land_idx, release_data_idx - 20))
    left_foot_land_idx = max(right_foot_land_idx + 1, min(left_foot_land_idx, release_data_idx - 10))
    
    # ============ 7. 构建阶段数据 ============
    prep_start_time = safe_get_time(prep_start_data_idx)
    right_foot_off_time = safe_get_time(right_foot_off_idx)
    left_foot_off_time = safe_get_time(left_foot_off_idx)
    right_foot_land_time = safe_get_time(right_foot_land_idx)
    left_foot_land_time = safe_get_time(left_foot_land_idx)
    
    # 阶段1: Preparation (预备阶段) - 从预摆最大幅度到第一次右脚离地
    phases.append({
        'id': 'preparation',
        'name': '预备阶段',
        'name_en': 'Preparation',
        'start_time': round(prep_start_time, 3),
        'end_time': round(right_foot_off_time, 3),
        'start_frame': prep_start_idx,
        'end_frame': data_to_discus_idx(right_foot_off_idx),
        'color': PHASE_COLORS['preparation'],
        'metrics': {
            'duration': round(right_foot_off_time - prep_start_time, 3),
            'description': '预摆最大幅度 → 右脚离地'
        }
    })
    
    # 阶段2: Entry (进入旋转阶段) - 从右脚离地到左脚离地
    phases.append({
        'id': 'entry',
        'name': '进入旋转',
        'name_en': 'Entry',
        'start_time': round(right_foot_off_time, 3),
        'end_time': round(left_foot_off_time, 3),
        'start_frame': data_to_discus_idx(right_foot_off_idx),
        'end_frame': data_to_discus_idx(left_foot_off_idx),
        'color': PHASE_COLORS['entry'],
        'metrics': {
            'duration': round(left_foot_off_time - right_foot_off_time, 3),
            'description': '右脚离地 → 左脚离地'
        }
    })
    
    # 阶段3: Airborne (腾空阶段) - 从双脚离地到右脚落地
    phases.append({
        'id': 'airborne',
        'name': '腾空阶段',
        'name_en': 'Airborne',
        'start_time': round(left_foot_off_time, 3),
        'end_time': round(right_foot_land_time, 3),
        'start_frame': data_to_discus_idx(left_foot_off_idx),
        'end_frame': data_to_discus_idx(right_foot_land_idx),
        'color': PHASE_COLORS['airborne'],
        'metrics': {
            'duration': round(right_foot_land_time - left_foot_off_time, 3),
            'flight_time': round(right_foot_land_time - left_foot_off_time, 3),
            'description': '双脚离地 → 右脚落地'
        }
    })
    
    # 阶段4: Transition (过渡阶段) - 从右脚落地到左脚落地
    phases.append({
        'id': 'transition',
        'name': '过渡阶段',
        'name_en': 'Transition',
        'start_time': round(right_foot_land_time, 3),
        'end_time': round(left_foot_land_time, 3),
        'start_frame': data_to_discus_idx(right_foot_land_idx),
        'end_frame': data_to_discus_idx(left_foot_land_idx),
        'color': PHASE_COLORS['transition'],
        'metrics': {
            'duration': round(left_foot_land_time - right_foot_land_time, 3),
            'description': '右脚落地 → 左脚落地'
        }
    })
    
    # 阶段5: Delivery (最后用力阶段) - 从左脚落地到出手
    phases.append({
        'id': 'delivery',
        'name': '最后用力',
        'name_en': 'Delivery',
        'start_time': round(left_foot_land_time, 3),
        'end_time': round(release_time, 3),
        'start_frame': data_to_discus_idx(left_foot_land_idx),
        'end_frame': release_idx,
        'color': PHASE_COLORS['delivery'],
        'metrics': {
            'duration': round(release_time - left_foot_land_time, 3),
            'release_speed': round(release_point['speed'], 2),
            'description': '左脚落地 → 出手'
        }
    })
    
    # 打印检测到的关键帧信息（用于调试）
    print(f"\n关键帧检测结果:")
    print(f"  预摆最大位置: 帧{prep_start_idx}, 时间{prep_start_time:.3f}s")
    print(f"  右脚离地: 帧{data_to_discus_idx(right_foot_off_idx)}, 时间{right_foot_off_time:.3f}s")
    print(f"  左脚离地: 帧{data_to_discus_idx(left_foot_off_idx)}, 时间{left_foot_off_time:.3f}s")
    print(f"  右脚落地: 帧{data_to_discus_idx(right_foot_land_idx)}, 时间{right_foot_land_time:.3f}s")
    print(f"  左脚落地: 帧{data_to_discus_idx(left_foot_land_idx)}, 时间{left_foot_land_time:.3f}s")
    print(f"  出手: 帧{release_idx}, 时间{release_time:.3f}s")
    
    return phases

def downsample_data(data_dict, target_points=600):
    """降采样数据"""
    n = len(data_dict['positions'])
    if n <= target_points:
        return data_dict
    
    step = max(1, n // target_points)
    
    result = {
        'times': data_dict['times'][::step],
        'positions': data_dict['positions'][::step],
        'speeds': data_dict['speeds'][::step]
    }
    
    if 'velocities' in data_dict:
        result['velocities'] = data_dict['velocities'][::step]
    
    return result

def downsample_skeleton(skeleton_data, target_points=600):
    """降采样骨架数据"""
    n = len(skeleton_data['frames'])
    if n <= target_points:
        return skeleton_data
    
    step = max(1, n // target_points)
    
    return {
        'frames': skeleton_data['frames'][::step],
        'bones': skeleton_data['bones'],
        'joint_names': skeleton_data['joint_names']
    }

def downsample_rotation(rotation_data, target_points=600):
    """降采样旋转数据"""
    n = len(rotation_data['frames'])
    if n <= target_points:
        return rotation_data
    
    step = max(1, n // target_points)
    
    return {
        'frames': rotation_data['frames'][::step],
        'joint_names': rotation_data['joint_names']
    }

def process_all_data(filepath, output_path, rotation_filepath=None):
    """主处理函数"""
    print(f"加载数据: {filepath}")
    data = load_data(filepath)
    print(f"有效数据行数: {len(data)}")
    
    if len(data) == 0:
        print("错误：没有有效数据！")
        return None
    
    print(f"时间范围: {data[0][COL_TIME]:.3f}s - {data[-1][COL_TIME]:.3f}s")
    
    print("\n提取铁饼轨迹...")
    discus_data = extract_discus_trajectory(data)
    print(f"铁饼轨迹点数: {len(discus_data['positions'])}")
    print(f"速度范围: {min(discus_data['speeds']):.2f} - {max(discus_data['speeds']):.2f} m/s")
    
    print("\n提取重心轨迹...")
    com_data = extract_com_trajectory(data)
    print(f"重心轨迹点数: {len(com_data['positions'])}")
    
    print("\n提取骨架数据...")
    skeleton_data = extract_skeleton_data(data)
    print(f"骨架帧数: {len(skeleton_data['frames'])}")
    print(f"关节点数: {len(skeleton_data['joint_names'])}")
    
    # 加载旋转数据
    rotation_data = None
    if rotation_filepath and os.path.exists(rotation_filepath):
        print(f"\n加载旋转数据: {rotation_filepath}")
        rotation_raw = load_rotation_data(rotation_filepath)
        print(f"旋转数据行数: {len(rotation_raw)}")
        rotation_data = extract_rotation_data(rotation_raw)
        print(f"旋转数据帧数: {len(rotation_data['frames'])}")
        print(f"旋转关节数: {len(rotation_data['joint_names'])}")
    
    print("\n提取关节速度数据...")
    joint_speeds = extract_joint_speeds(data)
    print(f"关节数: {len(joint_speeds)}")
    
    print("\n分析释放点...")
    release_point = find_release_point(discus_data, skeleton_data)
    print(f"释放点时间: {release_point['time']:.3f}s")
    print(f"释放点速度: {release_point['speed']:.2f} m/s")
    print(f"释放点位置: X={release_point['position'][0]:.2f}, Y={release_point['position'][1]:.2f}, Z={release_point['position'][2]:.2f}")
    
    print("\n计算生物力学指标...")
    biomechanics = calculate_biomechanics(discus_data, com_data, release_point)
    
    print("\n自动检测技术阶段...")
    times = [row[COL_TIME] for row in data]
    auto_phases = auto_detect_phases(data, discus_data, skeleton_data, release_point, times)
    print(f"检测到 {len(auto_phases)} 个技术阶段:")
    for phase in auto_phases:
        print(f"  - {phase['name']} ({phase['name_en']}): {phase['start_time']:.3f}s - {phase['end_time']:.3f}s")
    
    # 降采样
    discus_data_sampled = downsample_data(discus_data, 600)
    com_data_sampled = downsample_data(com_data, 600)
    skeleton_data_sampled = downsample_skeleton(skeleton_data, 600)
    
    # 降采样旋转数据
    rotation_data_sampled = None
    if rotation_data:
        rotation_data_sampled = downsample_rotation(rotation_data, 600)
    
    # 降采样关节速度数据
    joint_speeds_sampled = {}
    n = len(data)
    step = max(1, n // 600)
    for joint_name, joint_data in joint_speeds.items():
        joint_speeds_sampled[joint_name] = {
            'speeds': joint_data['speeds'][::step],
            'name_cn': joint_data['name_cn'],
            'max_speed': joint_data['max_speed'],
            'avg_speed': joint_data['avg_speed']
        }
    
    output_data = {
        'athlete': '姜志超',
        'event': '女子铁饼',
        'discus': discus_data_sampled,
        'com': com_data_sampled,
        'skeleton': skeleton_data_sampled,
        'rotation': rotation_data_sampled,  # 添加旋转数据
        'joint_speeds': joint_speeds_sampled,
        'release_point': release_point,
        'biomechanics': biomechanics,
        'auto_phases': auto_phases
    }
    
    print(f"\n保存数据到: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("铁饼投掷生物力学分析报告")
    print("="*60)
    print(f"运动员: 姜志超")
    print(f"项目: 女子铁饼")
    print("-"*60)
    print(f"  出手速度: {biomechanics['release_velocity']} m/s")
    print(f"  出手高度: {biomechanics['release_height']} m")
    print(f"  出手角度: {biomechanics['release_angle']}°")
    print(f"  旋转圈数: {biomechanics['rotation_count']} 圈")
    print(f"  最大速度: {biomechanics['max_speed']} m/s")
    print(f"  动作时间: {biomechanics['total_time']} s")
    print(f"  轨迹长度: {biomechanics['trajectory_length']} m")
    print("="*60)
    
    return output_data

if __name__ == '__main__':
    input_file = os.path.join(os.path.dirname(__file__), 'jzc/jzc1/all.txt')
    rotation_file = os.path.join(os.path.dirname(__file__), 'jzc/jzc3/rotation.txt')
    output_file = os.path.join(os.path.dirname(__file__), 'discus_data.json')
    
    process_all_data(input_file, output_file, rotation_file)
