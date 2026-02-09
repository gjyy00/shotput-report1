
import os
import sys

# Indices based on process_data.py
COL_TIME = 0
COL_ANKLE_R_Z = 49 + 2  # 51
COL_ANKLE_L_Z = 85 + 2  # 87

def load_data(filepath):
    data = []
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[2:]:
            parts = line.strip().split('\t')
            if len(parts) > 100:
                try:
                    values = [float(x) if x else 0.0 for x in parts]
                    if values[0] > 0:
                        data.append(values)
                except ValueError:
                    continue
    return data

def find_phases(data, release_time_target=2.26):
    # 1. Find Release Index
    release_idx = -1
    min_diff = float('inf')
    for i, row in enumerate(data):
        diff = abs(row[COL_TIME] - release_time_target)
        if diff < min_diff:
            min_diff = diff
            release_idx = i
            
    print(f"Release Time Target: {release_time_target}s")
    print(f"Actual Release Time: {data[release_idx][COL_TIME]:.3f}s (Index: {release_idx})")
    
    # Threshold for foot off ground (m)
    # Using 0.15m as per process_data.py, but we can adjust if needed
    TAKEOFF_THRESHOLD = 0.15
    
    foot_r_z = [row[COL_ANKLE_R_Z] for row in data]
    foot_l_z = [row[COL_ANKLE_L_Z] for row in data]
    times = [row[COL_TIME] for row in data]
    
    # 2. Find Right Foot Off (First time > Threshold)
    # Search from beginning
    right_off_idx = -1
    for i in range(release_idx):
        if foot_r_z[i] > TAKEOFF_THRESHOLD:
            # Check stability (next few frames also high)
            if all(z > TAKEOFF_THRESHOLD for z in foot_r_z[i:i+5]):
                right_off_idx = i
                break
    
    # 3. Find Left Foot Off (After Right Off)
    left_off_idx = -1
    start_search = right_off_idx if right_off_idx != -1 else 0
    for i in range(start_search + 5, release_idx):
        if foot_l_z[i] > TAKEOFF_THRESHOLD:
            if all(z > TAKEOFF_THRESHOLD for z in foot_l_z[i:i+5]):
                left_off_idx = i
                break
                
    # 4. Find Right Foot Land (After Left Off)
    right_land_idx = -1
    start_search = left_off_idx if left_off_idx != -1 else start_search + 10
    for i in range(start_search + 5, release_idx):
        if foot_r_z[i] < TAKEOFF_THRESHOLD:
            if all(z < TAKEOFF_THRESHOLD for z in foot_r_z[i:i+5]):
                right_land_idx = i
                break
                
    # 5. Find Left Foot Land (After Right Land)
    left_land_idx = -1
    start_search = right_land_idx if right_land_idx != -1 else start_search + 10
    for i in range(start_search + 5, release_idx):
        if foot_l_z[i] < TAKEOFF_THRESHOLD:
            if all(z < TAKEOFF_THRESHOLD for z in foot_l_z[i:i+5]):
                left_land_idx = i
                break

    # Output results
    events = [
        ("第一次右脚离地 (Right Foot Off)", right_off_idx),
        ("左脚离地 (Left Foot Off)", left_off_idx),
        ("右脚落地 (Right Foot Land)", right_land_idx),
        ("左脚落地 (Left Foot Land)", left_land_idx),
        ("出手 (Release)", release_idx)
    ]
    
    print("-" * 60)
    print(f"{'Event':<30} | {'Time (s)':<10} | {'Height (m)':<10}")
    print("-" * 60)
    
    for name, idx in events:
        if idx != -1:
            t = times[idx]
            h_r = foot_r_z[idx]
            h_l = foot_l_z[idx]
            h_info = f"R:{h_r:.2f} L:{h_l:.2f}"
            print(f"{name:<30} | {t:<10.3f} | {h_info:<10}")
        else:
            print(f"{name:<30} | {'Not Found':<10} | {'-':<10}")

    # Print data around detected points for verification
    print("\nDetailed Data Check:")
    for name, idx in events[:-1]: # Skip release for detail check as we know it
        if idx != -1:
            print(f"\nAround {name} ({times[idx]:.3f}s):")
            print(f"{'Time':<8} | {'R_Ankle_Z':<10} | {'L_Ankle_Z':<10}")
            for i in range(max(0, idx-3), min(len(data), idx+4)):
                marker = "<<" if i == idx else ""
                print(f"{times[i]:<8.3f} | {foot_r_z[i]:<10.3f} | {foot_l_z[i]:<10.3f} {marker}")

if __name__ == '__main__':
    # 改为分析 4.txt，目标出手时间设为之前确定的最佳点 2.92s
    filepath = '/Users/jiahongxiang/shotput_report_demo/4.txt'
    data = load_data(filepath)
    if data:
        find_phases(data, release_time_target=2.92)
