
const fs = require('fs');
const path = require('path');

const files = ['1.txt', '2.txt', '3.txt', '4.txt'];

const FIELD_PATTERNS = {
    // 重心相关
    'COG_X': ['CenterOfGravity X', '/Calc/CenterOfGravity X'],
    'COG_Y': ['CenterOfGravity Y', '/Calc/CenterOfGravity Y'],
    'COG_Z': ['CenterOfGravity Z', '/Calc/CenterOfGravity Z'],
    'COG_VX': ['CenterOfGravity v(X)', '/Calc/CenterOfGravity v(X)'],
    'COG_VY': ['CenterOfGravity v(Y)', '/Calc/CenterOfGravity v(Y)'],
    'COG_VZ': ['CenterOfGravity v(Z)', '/Calc/CenterOfGravity v(Z)'],
    'COG_V': ['CenterOfGravity v(绝对值)', '/Calc/CenterOfGravity v(绝对值)'],
    // 右手（铁饼）相关
    'HAND_R_X': ['Hand/Index/Base/Right X', '/Feature/Hand/Index/Base/Right X'],
    'HAND_R_Y': ['Hand/Index/Base/Right Y', '/Feature/Hand/Index/Base/Right Y'],
    'HAND_R_Z': ['Hand/Index/Base/Right Z', '/Feature/Hand/Index/Base/Right Z'],
    'HAND_R_VX': ['Hand/Index/Base/Right v(X)', '/Feature/Hand/Index/Base/Right v(X)'],
    'HAND_R_VY': ['Hand/Index/Base/Right v(Y)', '/Feature/Hand/Index/Base/Right v(Y)'],
    'HAND_R_VZ': ['Hand/Index/Base/Right v(Z)', '/Feature/Hand/Index/Base/Right v(Z)'],
    'HAND_R_V': ['Hand/Index/Base/Right v(绝对值)', '/Feature/Hand/Index/Base/Right v(绝对值)'],
};

const SKELETON_FIELD_PATTERNS = {
    'root': ['/Joint/Root X'],
    'pelvis': ['/Joint/Hip/Center X', '/Joint/Pelvis X'],
    'spine_low': ['/Joint/Spine/Lower X', '/Joint/Spine/Low X', '/Feature/Spine/Low X'],
    'spine_high': ['/Joint/Spine/Upper X', '/Joint/Spine/High X', '/Feature/Spine/High X'],
    'torso': ['/Joint/Torso X', '/Joint/Chest X'],
    'neck': ['/Joint/Neck X'],
    'head': ['/Joint/Head X', '/Joint/Skullbase X'],
    'clavicle_r': ['/Joint/Clavicle/Right X', '/Feature/Clavicle/Right X', '/Joint/Clavicular/Right X'],
    'shoulder_r': ['/Joint/Shoulder/Right X'],
    'elbow_r': ['/Joint/Elbow/Right X'],
    'wrist_r': ['/Joint/Wrist/Right X'],
    'hand_index_r': ['/Feature/Hand/Index/Base/Right X'],
    'hand_little_r': ['/Feature/Hand/Little/Base/Right X'],
    'clavicle_l': ['/Joint/Clavicle/Left X', '/Feature/Clavicle/Left X', '/Joint/Clavicular/Left X'],
    'shoulder_l': ['/Joint/Shoulder/Left X'],
    'elbow_l': ['/Joint/Elbow/Left X'],
    'wrist_l': ['/Joint/Wrist/Left X'],
    'hand_index_l': ['/Feature/Hand/Index/Base/Left X'],
    'hand_little_l': ['/Feature/Hand/Little/Base/Left X'],
    'hip_r': ['/Joint/Hip/Right X'],
    'knee_r': ['/Joint/Knee/Right X'],
    'ankle_r': ['/Joint/Ankle/Right X'],
    'foot_r': ['/Joint/Foot/Right X', '/Feature/Foot/Right X', '/Joint/Midfoot/Right X'],
    'hip_l': ['/Joint/Hip/Left X'],
    'knee_l': ['/Joint/Knee/Left X'],
    'ankle_l': ['/Joint/Ankle/Left X'],
    'foot_l': ['/Joint/Foot/Left X', '/Feature/Foot/Left X', '/Joint/Midfoot/Left X'],
};

function isUniformRow(row) {
    const sampleSize = Math.min(50, row.length);
    const vals = [];
    for (let i = 0; i < sampleSize; i++) {
        const v = typeof row[i] === 'string' ? parseFloat(row[i]) : row[i];
        if (!isNaN(v)) vals.push(v);
    }
    if (vals.length < 10) return false;
    const firstVal = vals[0];
    const sameCount = vals.filter(v => Math.abs(v - firstVal) < 0.001).length;
    return sameCount > vals.length * 0.8;
}

function findValidSampleRow(lines, maxSearch = 20) {
    for (let i = 1; i < Math.min(lines.length, maxSearch); i++) {
        const row = lines[i].trim().split('\t');
        if (row.length > 10 && !isNaN(parseFloat(row[0])) && parseFloat(row[0]) > 0) {
            if (!isUniformRow(row)) {
                return row;
            }
        }
    }
    return null;
}

function detectFieldPositions(headerRow, sampleDataRow = null) {
    const detected = {
        success: true,
        fields: {},
        skeletonJoints: {},
        missing: [],
        found: []
    };
    
    function findAllMatches(pattern) {
        const matches = [];
        for (let i = 0; i < headerRow.length; i++) {
            if (headerRow[i].includes(pattern) || headerRow[i] === pattern) {
                matches.push(i);
            }
        }
        return matches;
    }
    
    function selectValidIndex(matches, isZColumn = false) {
        if (matches.length === 0) return -1;
        if (matches.length === 1 || !sampleDataRow) return matches[0];
        
        for (const idx of matches) {
            const zIdx = idx + 2; // X列+2=Z列
            if (zIdx < sampleDataRow.length) {
                const zValue = parseFloat(sampleDataRow[zIdx]);
                if (!isNaN(zValue) && zValue >= 0 && zValue <= 2.5) {
                    return idx;
                }
            }
        }
        return matches[0];
    }
    
    for (const [fieldKey, patterns] of Object.entries(FIELD_PATTERNS)) {
        let foundIndex = -1;
        for (const pattern of patterns) {
            const matches = findAllMatches(pattern);
            if (matches.length > 0) {
                foundIndex = selectValidIndex(matches);
                break;
            }
        }
        detected.fields[fieldKey] = foundIndex;
        if (foundIndex === -1) {
            detected.missing.push(fieldKey);
        } else {
            detected.found.push(`${fieldKey}: 列${foundIndex}`);
        }
    }
    
    for (const [jointName, patterns] of Object.entries(SKELETON_FIELD_PATTERNS)) {
        let foundIndex = -1;
        for (const pattern of patterns) {
            const matches = findAllMatches(pattern);
            if (matches.length > 0) {
                foundIndex = selectValidIndex(matches);
                break;
            }
        }
        detected.skeletonJoints[jointName] = foundIndex;
        if (foundIndex === -1) {
            // console.warn(`骨架关节 ${jointName} 未找到`);
        }
    }
    
    const criticalFields = ['HAND_R_X', 'HAND_R_Y', 'HAND_R_Z'];
    const missingCritical = criticalFields.filter(f => detected.fields[f] === -1);
    if (missingCritical.length > 0) {
        detected.success = false;
    }
    
    return detected;
}

files.forEach(file => {
    console.log(`Checking ${file}...`);
    try {
        const content = fs.readFileSync(path.join(__dirname, file), 'utf-8');
        const lines = content.split('\n');
        
        if (lines.length === 0) {
            console.error(`Error: ${file} is empty`);
            return;
        }
        
        const headerRow = lines[0].trim().split('\t');
        const sampleDataRow = findValidSampleRow(lines);
        
        if (!sampleDataRow) {
            console.warn(`Warning: Could not find valid sample data row in ${file}`);
        }
        
        const detected = detectFieldPositions(headerRow, sampleDataRow);
        
        if (detected.success) {
            console.log(`[PASS] ${file}: All critical fields found.`);
            const handXIdx = detected.fields['HAND_R_X'];
            const handYIdx = detected.fields['HAND_R_Y'];
            const handZIdx = detected.fields['HAND_R_Z'];
            console.log(`  Hand R Index: ${handXIdx}, ${handYIdx}, ${handZIdx}`);
            
            // Check data values
            let validRows = 0;
            let zeroRows = 0;
            let uniformRows = 0;
            let timeRegressions = 0;
            let acceptedRows = 0;
            let lastTime = -Infinity;
            
            for (let i = 2; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;
                const parts = line.split('\t');
                if (parts.length > 100) {
                    const values = parts.map(x => x ? parseFloat(x) : 0.0);
                    
                    if (isUniformRow(values)) {
                        uniformRows++;
                        continue;
                    }
                    
                    if (values[0] > 0) { // Time > 0
                        const x = values[handXIdx];
                        const y = values[handYIdx];
                        const z = values[handZIdx];
                        
                        if (Math.abs(x) < 0.01 && Math.abs(y) < 0.01 && Math.abs(z) < 0.01) {
                            zeroRows++;
                        } else {
                            validRows++;
                        }
                        
                        if (values[0] > lastTime) {
                            acceptedRows++;
                            lastTime = values[0];
                        } else {
                            timeRegressions++;
                        }
                    }
                }
            }
            console.log(`  Data Check (ALL lines):`);
            console.log(`    Total Data Rows: ${validRows + zeroRows + uniformRows}`);
            console.log(`    Uniform Rows (skipped): ${uniformRows}`);
            console.log(`    Time Regressions (skipped): ${timeRegressions}`);
            console.log(`    Accepted Rows: ${acceptedRows}`);
            console.log(`    Zero Hand Rows (included): ${zeroRows}`);
            
            if (acceptedRows < 100) {
                console.warn(`  WARNING: Too few accepted rows (${acceptedRows})!`);
            }
            
            if (detected.missing.length > 0) {
                console.log(`  Missing optional fields: ${detected.missing.join(', ')}`);
            }
        } else {
            console.error(`[FAIL] ${file}: Missing critical fields!`);
            console.error(`  Missing: ${detected.missing.join(', ')}`);
        }
        
        // Count skeleton joints
        const skeletonCount = Object.values(detected.skeletonJoints).filter(v => v !== -1).length;
        console.log(`  Skeleton joints found: ${skeletonCount}/${Object.keys(SKELETON_FIELD_PATTERNS).length}`);
        
    } catch (e) {
        console.error(`Error reading/parsing ${file}: ${e.message}`);
    }
    console.log('---');
});
