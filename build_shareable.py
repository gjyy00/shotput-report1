import base64
import os
import re

def create_shareable_html():
    # 1. 读取 HTML 模板 (当前的 index.html)
    with open('index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    # 2. 内联 angle_data.js
    with open('angle_data.js', 'r', encoding='utf-8') as f:
        js_data = f.read()
    
    # 替换 <script src="angle_data.js"></script>
    html_content = html_content.replace('<script src="angle_data.js"></script>', f'<script>\n{js_data}\n</script>')

    # 2.5 针对国内网络环境优化 (移除 Google Fonts，替换 CDN)
    # 移除 Google Fonts
    html_content = re.sub(r'@import url\(\'https://fonts\.googleapis\.com/css2\?.*?\'\);', '', html_content)
    
    # 替换为国内 CDN (BootCDN)
    html_content = html_content.replace(
        'https://cdn.jsdelivr.net/npm/chart.js',
        'https://cdn.bootcdn.net/ajax/libs/Chart.js/4.4.1/chart.umd.min.js'
    )
    html_content = html_content.replace(
        'https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0',
        'https://cdn.bootcdn.net/ajax/libs/chartjs-plugin-datalabels/2.2.0/chartjs-plugin-datalabels.min.js'
    )

    # 3. 内联 GIF 图片
    gif_map = {
        'jzc/20260209213416.gif': 'jzc/20260209213416.gif',
        'jzc/20260209213835.gif': 'jzc/20260209213835.gif',
        'jzc/20260209214118.gif': 'jzc/20260209214118.gif'
    }

    for src_path, file_path in gif_map.items():
        if os.path.exists(file_path):
            with open(file_path, 'rb') as img_f:
                b64_data = base64.b64encode(img_f.read()).decode('utf-8')
                data_uri = f'data:image/gif;base64,{b64_data}'
                # 替换 src="..."
                html_content = html_content.replace(src_path, data_uri)
        else:
            print(f"Warning: Image not found {file_path}")

    # 4. 写入新文件
    output_filename = 'shareable_report.html'
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Successfully created {output_filename} with inlined resources.")

if __name__ == '__main__':
    create_shareable_html()
