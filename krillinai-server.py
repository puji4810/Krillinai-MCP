# krillinai_server.py
from mcp.server.fastmcp import FastMCP, Context
import httpx
import os
import base64
import mimetypes
from typing import Optional, List, Union, Dict, Any, Literal
import argparse

# 创建 FastMCP 服务器实例
mcp = FastMCP("KrillinaiConnector")
# --- Krillinai API 基础 URL ---
KRILLINAI_BASE_URL: str = "http://127.0.0.1:8888"

# --- Helper Function to make requests to Krillinai ---
async def _krillinai_request(method: str, endpoint: str, **kwargs) -> httpx.Response:
    """统一处理对 Krillinai API 的请求"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        url = f"{KRILLINAI_BASE_URL}{endpoint}"
        
        log_kwargs = {k: v for k, v in kwargs.items() if k != "files"} 
        print(f"向 Krillinai 发起请求: {method} {url} with {log_kwargs}")

        try:
            if method.upper() == "GET":
                response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await client.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            print(f"Krillinai API HTTP Error for {method} {url}: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            print(f"Krillinai API Request Error for {method} {url}: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error during Krillinai API call for {method} {url}: {str(e)}")
            raise

# --- MCP Tools ---

# --- 配置管理工具 ---
@mcp.tool()
async def get_krillinai_configuration(ctx: Context) -> dict:
    """
    获取当前 Krillin 连接器配置，主要是 Krillin 服务的 BASE URL。
    """
    global KRILLINAI_BASE_URL
    ctx.info(f"获取当前 Krillin BASE URL: {KRILLINAI_BASE_URL}")
    return {
        "error": 0,
        "msg": "当前配置获取成功",
        "data": {
            "krillinai_base_url": KRILLINAI_BASE_URL
        }
    }

@mcp.tool()
async def set_krillinai_base_url(ctx: Context, new_url: str) -> dict:
    """
    设置 Krillinai 服务的 BASE URL。
    注意: 此更改将影响当前 MCP 服务器实例后续所有对 Krillinai 的调用。

    Args:
        new_url: 新的 Krillinai 服务 BASE URL (例如 "http://localhost:8889" 或 "http://remote.krillinai.server").
                 请确保 URL 格式正确且服务可达。
    """
    global KRILLINAI_BASE_URL
    previous_url = KRILLINAI_BASE_URL
    
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        msg = "设置失败：URL 格式不正确，应以 http:// 或 https:// 开头。"
        ctx.error(msg)
        return {"error": 1, "msg": msg, "data": {"previous_url": previous_url}}

    KRILLINAI_BASE_URL = new_url.rstrip('/') # 存储时移除末尾斜杠
    msg = f"Krillinai BASE URL 已从 '{previous_url}' 更新为 '{KRILLINAI_BASE_URL}'。"
    ctx.info(msg)
    return {
        "error": 0,
        "msg": msg,
        "data": {
            "new_krillinai_base_url": KRILLINAI_BASE_URL,
            "previous_krillinai_base_url": previous_url
        }
    }

@mcp.tool()
async def upload_file_to_krillinai(ctx: Context, server_accessible_file_path: str) -> dict:
    """
    将 MCP 服务器可访问路径下的文件上传到 Krillinai 服务。
    可用于上传视频进行字幕处理，或上传音频进行音色克隆。

    Args:
        server_accessible_file_path: 文件在 MCP 服务器文件系统上的绝对路径。
                                     LLM 需要确保文件已通过某种方式放置在此路径。
    Returns:
        一个包含 Krillinai 服务上文件路径的字典，或错误信息。
    """
    try:
        if not os.path.exists(server_accessible_file_path):
            return {"error": 1, "msg": f"文件未找到: {server_accessible_file_path}", "data": None}
        
        file_name = os.path.basename(server_accessible_file_path)
        
        with open(server_accessible_file_path, "rb") as f:
            file_content = f.read()
            
        mime_type, _ = mimetypes.guess_type(server_accessible_file_path)
        if mime_type is None:
            if file_name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                mime_type = 'video/mp4' # 常用视频MIME
            elif file_name.lower().endswith(('.mp3', '.wav', '.aac', '.m4a')):
                mime_type = 'audio/mpeg' # 常用音频MIME
            else:
                mime_type = 'application/octet-stream'
            
        files_param = {"file": (file_name, file_content, mime_type)}
        
        ctx.info(f"准备上传文件: {file_name} (MIME: {mime_type}) 到 Krillinai...")
        response = await _krillinai_request("POST", "/api/file", files=files_param)
        krillinai_response = response.json()
        ctx.info(f"Krillinai 文件上传响应: {krillinai_response}")
        if krillinai_response.get("data") and isinstance(krillinai_response["data"].get("file_path"), str):
            krillinai_response["data"]["file_path"] = krillinai_response["data"]["file_path"][0]

        return krillinai_response
            
    except Exception as e:
        ctx.error(f"上传文件到 Krillinai 失败: {str(e)}")
        return {"error": 1, "msg": f"上传文件失败: {str(e)}", "data": None}


# 定义源语言的 Literal 类型
SourceLanguage = Literal["zh_cn", "en", "ja", "tr", "de", "ko", "ru"]

PartialTranslationLanguage = Literal[
    "zh_cn", "zh_tw", "en", "ja", "pinyin", "mid", "ms", "th", "vi", "fil", 
    "ko", "ar", "fr", "de", "it", "ru", "pt", "es", "hi", "bn", "he", "fa", 
    "af", "sv", "fi", "da", "no", "nl", "el", "uk", "hu", "pl", "tr", "sr", 
    "hr", "cs", "sw", "yo", "ha", "am", "om", "is", "lb", "ca", "ro", "ro2", 
    "sk", "bs", "mk", "sl", "bg", "lv", "lt", "et", "mt", "sq"
]

@mcp.tool()
async def start_krillinai_subtitle_task(
    ctx: Context,
    media_url_on_krillinai: str,
    language: SourceLanguage = "zh_cn",
    origin_lang: Optional[SourceLanguage] = None,
    target_lang: Optional[str] = None,
    bilingual: bool = False,
    translation_subtitle_pos: Literal[1, 2] = 1,
    tts: bool = False,
    tts_voice_code: Optional[Literal[1, 2]] = None,
    tts_voice_clone_src_file_url: Optional[str] = None,
    modal_filter: bool = False,
    embed_subtitle_video_type: Literal["horizontal", "vertical", "all", "none"] = "none",
    vertical_major_title: Optional[str] = None,
    vertical_minor_title: Optional[str] = None,
    replace_words: Optional[List[str]] = None
) -> dict:
    """
    为 Krillinai 服务上已上传的媒体文件或外部链接启动字幕处理任务。

    Args:
        media_url_on_krillinai: Krillinai 服务上的媒体文件路径 (例如 "local:./uploads/video.mp4") 或可访问的外部媒体链接。
        language: 媒体内容的源语言或主要识别语言。
                  可选值: "zh_cn" (简体中文), "en" (英文), "ja" (日文), "tr" (土耳其语), "de" (德语), "ko" (韩语), "ru" (俄语)。
                  默认为 "zh_cn"。
        origin_lang: 可选，进行翻译时的源语言。如果启用翻译且未提供此项，可能默认为 `language` 参数的值。
                     可选值同 `language` 参数。
        target_lang: 可选，进行翻译时的目标语言。如果提供了此参数，表示需要翻译。
                     可用值非常广泛，例如 "zh_cn", "zh_tw", "en", "ja", "pinyin", "fr", "es", "de" 等（请参考您之前提供的完整前端HTML列表）。
        bilingual: 是否生成双语字幕。True 表示启用 (发送 1 给 Krillinai)，False 表示不启用 (发送 2 给 Krillinai)。默认为 False。
        translation_subtitle_pos: 双语字幕时，翻译字幕的位置。1 = 翻译字幕在上, 2 = 翻译字幕在下。默认为 1。
        tts: 是否为字幕启用 TTS (文本转语音)。True 表示启用 (发送 1 给 Krillinai)，False 表示不启用 (发送 2 给 Krillinai)。默认为 False。
        tts_voice_code: 可选，TTS 使用的音色代码。例如 1 或 2。
        tts_voice_clone_src_file_url: 可选，用于 TTS 音色克隆的已上传音频文件在 Krillinai 上的路径。
        modal_filter: 是否过滤语气词等。True 表示启用 (发送 1 给 Krillinai)，False 表示不启用 (发送 2 给 Krillinai)。默认为 False。
        embed_subtitle_video_type: 字幕嵌入视频的类型。
                                   可选值: "horizontal", "vertical", "all", "none"。默认为 "none"。
        vertical_major_title: 可选，当 embed_subtitle_video_type 为 "vertical" 或 "all" 时，竖屏视频的主标题。
        vertical_minor_title: 可选，当 embed_subtitle_video_type 为 "vertical" 或 "all" 时，竖屏视频的副标题。
        replace_words: 可选，词语替换列表，格式为 ["原词1|替换词1", "原词2|替换词2", ...]。

    Returns:
        一个包含任务 ID 的字典，或错误信息。
    """
    try:
        payload: Dict[str, Any] = {
            "url": media_url_on_krillinai,
            "language": language,
            "bilingual": 1 if bilingual else 2,
            "translation_subtitle_pos": translation_subtitle_pos,
            "tts": 1 if tts else 2,
            "modal_filter": 1 if modal_filter else 2,
            "embed_subtitle_video_type": embed_subtitle_video_type,
        }
        if origin_lang:
            payload["origin_lang"] = origin_lang
        else:
            if target_lang: # 只有在需要翻译时，才考虑默认origin_lang
                 payload["origin_lang"] = language

        if target_lang:
            payload["target_lang"] = target_lang
        
        if payload["tts"] == 1: # 只有当 tts 实际要发送为 1 (启用) 时，才处理 tts 相关子参数
            if tts_voice_code is not None:
                payload["tts_voice_code"] = tts_voice_code
            if tts_voice_clone_src_file_url:
                payload["tts_voice_clone_src_file_url"] = tts_voice_clone_src_file_url
        
        if vertical_major_title is not None:
            payload["vertical_major_title"] = vertical_major_title
        if vertical_minor_title is not None:
            payload["vertical_minor_title"] = vertical_minor_title
        if replace_words:
            payload["replace"] = replace_words
            
        ctx.info(f"向 Krillinai 启动字幕任务，参数: {payload}")
        response = await _krillinai_request("POST", "/api/capability/subtitleTask", json=payload)
        krillinai_response = response.json()
        ctx.info(f"Krillinai 字幕任务启动响应: {krillinai_response}")
        return krillinai_response
    except Exception as e:
        ctx.error(f"启动 Krillinai 字幕任务失败: {str(e)}")
        return {"error": 1, "msg": f"启动字幕任务失败: {str(e)}", "data": None}

@mcp.tool()
async def get_krillinai_subtitle_task_details(ctx: Context, task_id: str) -> dict:
    """
    获取 Krillinai 字幕任务的当前状态、进度和结果（如果已完成）。
    如果任务完成且可能生成了嵌入字幕的视频，会尝试添加这些视频的潜在下载链接。
    请根据 start_krillinai_subtitle_task 时的参数来选择返回嵌入视频的链接

    Args:
        task_id: 要查询的任务 ID。
    Returns:
        一个包含任务详细信息的字典，包括状态、进度、字幕/语音下载链接，以及可能的嵌入字幕视频链接。
    """
    try:
        ctx.info(f"查询 Krillinai 字幕任务详情，Task ID: {task_id}")
        response = await _krillinai_request("GET", f"/api/capability/subtitleTask?taskId={task_id}")
        krillinai_response = response.json() # 这是从 Krillinai API 返回的原始响应
        
        # 我们将直接修改 krillinai_response 中的 data 部分来追加信息
        if krillinai_response.get("error") == 0 and "data" in krillinai_response:
            data_part = krillinai_response["data"] # 获取对 data 字典的引用
            
            progress = data_part.get("process_percent") # 不再使用 "N/A" 作为默认值
            ctx.info(f"Krillinai 任务 '{task_id}' 状态: progress {progress if progress is not None else '未知'}%")
            
            # 确保 subtitle_info 中的下载链接是完整的 URL
            if "subtitle_info" in data_part and isinstance(data_part["subtitle_info"], list):
                for item in data_part["subtitle_info"]:
                    if "download_url" in item and isinstance(item["download_url"], str) and not item["download_url"].startswith("http"):
                        relative_url = item["download_url"]
                        item["download_url"] = f"{KRILLINAI_BASE_URL.rstrip('/')}{relative_url}" if relative_url.startswith("/") else f"{KRILLINAI_BASE_URL.rstrip('/')}/{relative_url}"
            
            # 确保 speech_download_url 是完整的 URL
            if "speech_download_url" in data_part and isinstance(data_part["speech_download_url"], str) and data_part["speech_download_url"] and not data_part["speech_download_url"].startswith("http"):
                relative_url = data_part["speech_download_url"]
                data_part["speech_download_url"] = f"{KRILLINAI_BASE_URL.rstrip('/')}{relative_url}" if relative_url.startswith("/") else f"{KRILLINAI_BASE_URL.rstrip('/')}/{relative_url}"

            # 新增逻辑：如果任务完成，尝试添加嵌入字幕视频的推断下载链接
            if progress == 100:
                if "potential_embedded_video_urls" not in data_part: # 避免重复添加
                    data_part["potential_embedded_video_urls"] = []
                
                # 横屏视频链接
                h_embed_path = f"/api/file/tasks/{task_id}/output/horizontal_embed.mp4"
                data_part["potential_embedded_video_urls"].append({
                    "name": "嵌入字幕的横屏视频 (可能存在)",
                    "download_url": f"{KRILLINAI_BASE_URL.rstrip('/')}{h_embed_path}"
                })
                
                # 竖屏视频链接
                v_embed_path = f"/api/file/tasks/{task_id}/output/vertical_embed.mp4"
                data_part["potential_embedded_video_urls"].append({
                    "name": "嵌入字幕的竖屏视频 (可能存在)",
                    "download_url": f"{KRILLINAI_BASE_URL.rstrip('/')}{v_embed_path}"
                })
                ctx.info(f"为已完成的任务 {task_id} 添加了推断的嵌入视频下载链接。")
        
        return krillinai_response # 返回修改后的（可能已追加视频链接的）原始响应
    
    except Exception as e:
        error_msg = f"获取 Krillinai 字幕任务详情失败 (ID: {task_id}): {str(e)}"
        ctx.error(error_msg)
        return {"error": 1, "msg": error_msg, "data": {"task_id": task_id}}

# download_krillinai_file_content 工具不再需要，因为 get_krillinai_subtitle_task_details
# 会直接返回完整的可下载 URL。LLM 可以将这些 URL 直接呈现给用户。
# 如果确实需要 MCP 服务器代为下载并返回内容（例如，LLM无法直接处理URL下载的情况），
# 我们可以再实现一个版本，但首选是让客户端/用户直接使用 krillinai 提供的 URL。

# 如果您仍然希望有一个工具来代理下载并返回内容（例如，对于无法直接访问外部 URL 的受限 LLM 环境）：
@mcp.tool()
async def fetch_krillinai_file_as_text(ctx: Context, full_download_url: str) -> dict:
    """
    根据 Krillinai 提供的完整 URL 下载文件内容，并以文本形式返回。
    适用于字幕文件等小型文本文件。

    Args:
        full_download_url: Krillinai 任务结果中提供的完整可下载 HTTP/HTTPS URL。
    Returns:
        一个包含文件名、文本内容和MIME类型的字典，或错误信息。
    """
    try:
        ctx.info(f"准备从 Krillinai 下载并获取文本内容: {full_download_url}")
        
        # 这里不再需要 _krillinai_request，因为它是完整的外部 URL
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(full_download_url)
            response.raise_for_status()
        
        file_content_bytes = response.content
        # 尝试将内容解码为 UTF-8 文本，对于 SRT 等字幕文件通常是这样
        try:
            file_text_content = file_content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # 如果 UTF-8 解码失败，可以尝试其他编码或直接返回错误
            ctx.warning(f"文件 {full_download_url} UTF-8 解码失败，尝试 Latin-1")
            try:
                file_text_content = file_content_bytes.decode("latin-1")
            except UnicodeDecodeError:
                return {"error": 1, "msg": "文件内容无法解码为文本", "data": None}

        file_name = os.path.basename(httpx.URL(full_download_url).path) # 从URL中提取文件名
        mime_type = response.headers.get("content-type", "text/plain")

        ctx.info(f"文件 {file_name} (MIME: {mime_type}) 内容获取成功，长度: {len(file_content_bytes)} bytes.")
        return {
            "error": 0,
            "msg": "文件内容获取成功",
            "data": {
                "file_name": file_name,
                "text_content": file_text_content,
                "mime_type": mime_type,
            }
        }
    except Exception as e:
        ctx.error(f"从 Krillinai URL 下载文件内容失败 ({full_download_url}): {str(e)}")
        return {"error": 1, "msg": f"下载文件内容失败: {str(e)}", "data": None}

# --- Main Function ---
if __name__ == "__main__":
    # 默认的 Krillinai URL
    DEFAULT_KRILLINAI_URL = "http://127.0.0.1:8888"

    parser = argparse.ArgumentParser(description="MCP Server for Krillinai Connector")
    parser.add_argument(
        "--krillinai-url",
        type=str,
        # 如果命令行未提供，则尝试读取环境变量，否则使用硬编码的默认值
        default=os.getenv("KRILLINAI_URL", DEFAULT_KRILLINAI_URL),
        help=f"The base URL for the Krillinai service (e.g., http://localhost:8888). "
             f"Can also be set via KRILLINAI_URL environment variable. Default: {DEFAULT_KRILLINAI_URL}"
    )
    parser.add_argument(
        "--mcp-transport",
        type=str,
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="MCP transport type to use (default: stdio)"
    )
    parser.add_argument(
        "--mcp-host",
        type=str,
        default="0.0.0.0",
        help="Host for streamable-http transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=8001,
        help="Port for streamable-http transport (default: 8001)"
    )

    args = parser.parse_args()

    KRILLINAI_BASE_URL = args.krillinai_url.rstrip('/')

    print(f"Krillinai MCP 服务器启动中...")
    print(f"  将连接到 Krillinai 服务于: {KRILLINAI_BASE_URL}")
    print(f"  MCP Transport 类型: {args.mcp_transport}")
    if args.mcp_transport == "streamable-http":
        print(f"  MCP 服务将监听于: {args.mcp_host}:{args.mcp_port}/mcp")
        mcp.run(transport=args.mcp_transport, host=args.mcp_host, port=args.mcp_port)
    else: # stdio
        mcp.run(transport=args.mcp_transport)