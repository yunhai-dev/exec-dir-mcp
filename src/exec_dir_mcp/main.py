import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any, Optional, List
import sys
import os
import argparse


class MCPServer:
    """MCP 服务器，支持在指定文件夹执行命令"""
    
    def __init__(self, default_dir: str, allowed_dirs: Optional[List[str]] = None):
        self.initialized = False
        self.default_dir = default_dir
        self.allowed_dirs = allowed_dirs or []
        
        # 如果没有配置允许的目录，则允许所有目录
        self.allow_all = len(self.allowed_dirs) == 0
        
        sys.stderr.write(f"服务器配置:\n")
        sys.stderr.write(f"  默认目录: {self.default_dir}\n")
        sys.stderr.write(f"  允许的目录: {self.allowed_dirs if self.allowed_dirs else '全部'}\n")
        sys.stderr.flush()
    
    def is_directory_allowed(self, directory: str) -> tuple[bool, str]:
        """检查目录是否在允许列表中"""
        if self.allow_all:
            return True, ""
        
        dir_path = Path(directory).resolve()
        
        for allowed in self.allowed_dirs:
            allowed_path = Path(allowed).resolve()
            try:
                # 检查是否是允许目录的子目录
                dir_path.relative_to(allowed_path)
                return True, ""
            except ValueError:
                continue
        
        return False, f"目录不在允许列表中: {directory}"
    
    async def execute_command(
        self, 
        command: str, 
        working_dir: Optional[str] = None,
        timeout: int = 30
    ) -> dict[str, Any]:
        """在指定目录执行命令"""
        try:
            # 使用默认目录或指定目录
            target_dir = working_dir or self.default_dir
            
            # 验证工作目录
            work_path = Path(target_dir).resolve()
            if not work_path.exists():
                return {
                    "success": False,
                    "error": f"目录不存在: {target_dir}"
                }
            
            if not work_path.is_dir():
                return {
                    "success": False,
                    "error": f"路径不是目录: {target_dir}"
                }
            
            # 检查目录权限
            allowed, error_msg = self.is_directory_allowed(str(work_path))
            if not allowed:
                return {
                    "success": False,
                    "error": error_msg
                }
            
            sys.stderr.write(f"执行命令: {command}\n")
            sys.stderr.write(f"工作目录: {work_path}\n")
            sys.stderr.flush()
            
            # 执行命令
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_path)
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                return {
                    "success": True,
                    "stdout": stdout.decode('utf-8', errors='replace'),
                    "stderr": stderr.decode('utf-8', errors='replace'),
                    "returncode": process.returncode,
                    "working_dir": str(work_path),
                    "command": command
                }
            
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"命令执行超时（{timeout}秒）"
                }
        
        except Exception as e:
            sys.stderr.write(f"执行命令时出错: {e}\n")
            sys.stderr.flush()
            return {
                "success": False,
                "error": f"执行错误: {str(e)}"
            }
    
    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """处理 MCP 请求"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "initialize":
            self.initialized = True
            return {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "command-executor",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        
        elif method == "notifications/initialized":
            # 客户端通知初始化完成
            return None
        
        elif method == "tools/list":
            return {
                "tools": [
                    {
                        "name": "execute_command",
                        "description": f"在指定文件夹中执行命令。默认目录: {self.default_dir}",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "要执行的命令（shell 命令）"
                                },
                                "working_dir": {
                                    "type": "string",
                                    "description": f"工作目录的路径（可选，默认: {self.default_dir}）"
                                },
                                "timeout": {
                                    "type": "integer",
                                    "description": "超时时间（秒），默认30秒",
                                    "default": 30
                                }
                            },
                            "required": ["command"]
                        }
                    }
                ]
            }
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "execute_command":
                result = await self.execute_command(
                    command=arguments.get("command"),
                    working_dir=arguments.get("working_dir"),
                    timeout=arguments.get("timeout", 30)
                )
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2, ensure_ascii=False)
                        }
                    ]
                }
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"error": f"未知工具: {tool_name}"})
                    }
                ],
                "isError": True
            }
        
        return {
            "error": {
                "code": -32601,
                "message": f"未知方法: {method}"
            }
        }
    
    def send_response(self, response: dict[str, Any], request_id: Any = None):
        """发送响应到标准输出"""
        if response is None:
            return
        
        result = {
            "jsonrpc": "2.0"
        }
        
        if request_id is not None:
            result["id"] = request_id
        
        if "error" in response:
            result["error"] = response["error"]
        else:
            result["result"] = response
        
        output = json.dumps(result)
        print(output, flush=True)
        sys.stderr.write(f">>> 发送响应\n")
        sys.stderr.flush()
    
    async def run(self):
        """运行 MCP 服务器（标准输入/输出模式）"""
        sys.stderr.write("=" * 50 + "\n")
        sys.stderr.write("MCP 命令执行服务器已启动\n")
        sys.stderr.write("=" * 50 + "\n")
        sys.stderr.flush()
        
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                # 读取一行输入
                line = await loop.run_in_executor(None, sys.stdin.readline)
                
                if not line:
                    sys.stderr.write("输入流结束，退出服务器\n")
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                sys.stderr.write(f"<<< 收到请求: {request.get('method', 'unknown')}\n" if (request := json.loads(line)) else "<<< 收到请求\n")
                sys.stderr.flush()
                
                request_id = request.get("id")
                
                response = await self.handle_request(request)
                self.send_response(response, request_id)
            
            except json.JSONDecodeError as e:
                sys.stderr.write(f"JSON 解析错误: {e}\n")
                sys.stderr.flush()
                self.send_response({
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }, None)
            
            except Exception as e:
                sys.stderr.write(f"处理错误: {e}\n")
                sys.stderr.flush()
                self.send_response({
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }, None)


def main():
    parser = argparse.ArgumentParser(
        description='MCP 命令执行服务器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 默认目录为当前目录，允许所有目录
  python mcp_server.py
  
  # 指定默认目录
  python mcp_server.py --dir /home/user/projects
  
  # 指定默认目录和允许的目录列表
  python mcp_server.py --dir /home/user/projects --allowed /home/user/projects --allowed /tmp
        """
    )
    
    parser.add_argument(
        '--dir',
        type=str,
        default=os.getcwd(),
        help='默认工作目录（默认: 当前目录）'
    )
    
    parser.add_argument(
        '--allowed',
        type=str,
        action='append',
        help='允许执行命令的目录（可多次指定，不指定则允许所有目录）'
    )
    
    args = parser.parse_args()
    
    try:
        server = MCPServer(
            default_dir=args.dir,
            allowed_dirs=args.allowed
        )
        asyncio.run(server.run())
    except KeyboardInterrupt:
        sys.stderr.write("\n服务器已停止\n")
        sys.exit(0)


def entry_main():
    """入口函数，用于命令行调用"""
    main()


if __name__ == "__main__":
    main()
