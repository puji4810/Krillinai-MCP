# Krillinai MCP 服务器

KrillinAI MCP 服务器是一个基于 Model Context Protocol (MCP) 的连接器，用于与 KrillinAI 服务进行交互。该服务器充当大语言模型 (LLM) 与 KrillinAI 服务之间的桥梁，使 LLM 能够使用 KrillinAI 的字幕生成、翻译、TTS 等功能。

## 功能特点

- **文件上传**: 上传视频或音频文件到 KrillinAI 服务
- **字幕处理**: 为视频自动生成字幕
- **翻译功能**: 支持字幕翻译为多种语言
- **双语字幕**: 生成双语字幕，支持自定义翻译字幕位置
- **文本转语音(TTS)**: 为字幕生成语音，支持音色克隆
- **字幕嵌入**: 将字幕直接嵌入到视频中
- **语气词过滤**: 过滤语气词，提高字幕质量

## 安装要求

- Python 3.12 或更高版本
- KrillinAI 服务（默认运行在 http://127.0.0.1:8888）

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/krillinai-mcp-server.git
cd krillinai-mcp-server

# 使用 pip 安装依赖
pip install -e .

# 或者使用 uv 安装（推荐）
uv pip install -e .
```

## 使用方法

### 启动服务器

```bash
python krillinai-server.py
```

### 与 MCP 客户端集成

#### Claude Desktop 示例配置

要将此服务器集成到 Claude Desktop，您需要编辑其 MCP 服务器配置文件。 在 macOS 上，该文件通常位于`~/Library/Application Support/Claude/claude_desktop_config.json`。

```json
{
  "mcpServers": {
    "krillinai-mcp-server": {
      "isActive": true, // 设置为 true 来激活
      "name": "KrillinaiConnector", 
      "type": "stdio", // 如果使用 stdio
      "description": "Connects to Krillinai for subtitle and media processing.",
      "command": "/abs/path/to/your/project/.venv/bin/python", // 指向虚拟环境中的 Python 解释器
      "args": [
        "/abs/path/to/your/project/krillinai-server.py" // 指向您的服务器脚本
        // 如果需要，可以在这里传递命令行参数给您的脚本
        // 例如: "--krillai-url", "http://custom-krillai.local:8888"
      ],
      "env": { // 可选：如果通过环境变量配置 Krillinai URL
        // "KRILLINAI_URL": "http://localhost:8888"
      }
    }
    // 您可能还有其他 MCP 服务器配置...
  }
}
```

**请务必将** **`/abs/path/to/your/project/` 替换为您的实际项目路径。**

### 命令行选项

- `--krillinai-url`: 指定 KrillinAI 服务的 URL (默认: http://127.0.0.1:8888)
- `--mcp-transport`: 指定 MCP 传输类型，可选 "stdio"(默认) 或 "streamable-http"
- `--mcp-host`: 指定 HTTP 服务器主机（仅当 mcp-transport 为 "streamable-http" 时有效）
- `--mcp-port`: 指定 HTTP 服务器端口（仅当 mcp-transport 为 "streamable-http" 时有效）

示例:

```bash
# 使用环境变量设置 KrillinAI URL
export KRILLINAI_URL="http://192.168.1.100:8888"
python krillinai-server.py

# 或者直接通过命令行参数设置
python krillinai-server.py --krillinai-url="http://192.168.1.100:8888"

# 使用 HTTP 传输并指定端口
python krillinai-server.py --mcp-transport="streamable-http" --mcp-port=8001
```

## MCP 工具

该服务器提供了以下 MCP 工具供 LLM 使用：

1. **配置管理工具**

   - `get_krillinai_configuration`: 获取当前 KrillinAI 连接配置
   - `set_krillinai_base_url`: 设置 KrillinAI 服务的 BASE URL
2. **文件处理工具**

   - `upload_file_to_krillinai`: 将服务器可访问的文件上传到 KrillinAI
3. **字幕处理工具**

   - `start_krillinai_subtitle_task`: 启动字幕处理任务
   - `get_krillinai_subtitle_task_details`: 获取字幕任务详情
4. **内容获取工具**

   - `fetch_krillinai_file_as_text`: 获取 KrillinAI 文件的文本内容

## 工作流程示例

1. 上传视频文件
2. 启动字幕处理任务（可设置语言、翻译等参数）
3. 查询任务状态直至完成
4. 获取生成的字幕文件、语音或嵌入字幕的视频
